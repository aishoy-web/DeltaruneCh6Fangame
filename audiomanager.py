import pygame
import numpy as np

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
class AudioManager:
    def __init__(self):
        pygame.mixer.init()
        self.current_music = None
        self.music_volume = 0.5
        self.pitched_sound_cache = {}
    def play_music(self, filename, loop=True):
        music_path = BASE_DIR / "mus" / filename
        if self.current_music == filename:
            return  # Don't restart the same song
        # print("Loading music:", music_path)
        # with open(music_path, "rb") as file:
            # print("Audio header:", file.read(12))
        pygame.mixer.music.load(music_path)
        pygame.mixer.music.set_volume(self.music_volume)
        loops = -1 if loop else 0
        pygame.mixer.music.play(loops)
        self.current_music = filename
    def stop_music(self):
        pygame.mixer.music.stop()
        self.current_music = None
    def fade_out(self, duration=1000):
        pygame.mixer.music.fadeout(duration)
    def change_music(self, filename):
        if self.current_music == filename:
            return
        pygame.mixer.music.fadeout(500)
        self.game.root.after(
        500,
        lambda: self.play_music(filename))
    def play_sfx(self, filename):
        sound = pygame.mixer.Sound(
            BASE_DIR / "audio" / "sfx" / filename
        )
        sound.play()
    def pitch_shift_sound(self, sound, pitch=1.0):
        """
        Return a new pygame Sound with its playback pitch changed.
        pitch:
            1.0 = normal
            2.0 = one octave higher / twice as fast
            0.5 = one octave lower / twice as slow
        This changes pitch and duration together, like changing
        playback speed.
        """
        pitch = float(pitch)
        if pitch <= 0:
            raise ValueError("pitch must be greater than 0")
        if abs(pitch - 1.0) < 0.0001:
            return sound
        samples = pygame.sndarray.array(
            sound
        )
        source_length = samples.shape[0]
        if source_length <= 1:
            return sound
        target_length = max(
            1,
            round(
                source_length / pitch
            )
        )
        old_positions = np.arange(
            source_length,
            dtype=np.float64
        )
        new_positions = np.linspace(
            0,
            source_length - 1,
            target_length
        )
        # ----------------------------------------------
        # Mono
        # ----------------------------------------------
        if samples.ndim == 1:
            shifted = np.interp(
                new_positions,
                old_positions,
                samples
            )
        # ----------------------------------------------
        # Stereo / multichannel
        # ----------------------------------------------
        else:
            channel_count = samples.shape[1]
            shifted = np.empty(
                (
                    target_length,
                    channel_count
                ),
                dtype=np.float64
            )
            for channel in range(
                channel_count
            ):
                shifted[:, channel] = (
                    np.interp(
                        new_positions,
                        old_positions,
                        samples[:, channel]
                    )
                )
        # ----------------------------------------------
        # Convert back to the original PCM type
        # ----------------------------------------------
        if np.issubdtype(
            samples.dtype,
            np.integer
        ):
            limits = np.iinfo(
                samples.dtype
            )
            shifted = np.clip(
                shifted,
                limits.min,
                limits.max
            )
        shifted = shifted.astype(
            samples.dtype
        )
        shifted = np.ascontiguousarray(
            shifted
        )
        return pygame.sndarray.make_sound(
            shifted
        )
    def get_pitched_sound(
        self,
        sound_path,
        pitch=1.0,
    ):
        """
        Load and cache a pitched pygame Sound.

        The cache prevents the same audio file from being
        resampled every time it is played.
        """

        sound_path = Path(
            sound_path
        )

        pitch = float(
            pitch
        )

        cache_key = (
            str(
                sound_path.resolve()
            ),
            round(
                pitch,
                4
            ),
        )

        # ----------------------------------------------
        # Return cached version
        # ----------------------------------------------

        if cache_key in self.pitched_sound_cache:
            return self.pitched_sound_cache[
                cache_key
            ]

        # ----------------------------------------------
        # Load original sound
        # ----------------------------------------------

        sound = pygame.mixer.Sound(
            str(sound_path)
        )

        # ----------------------------------------------
        # Apply pitch
        # ----------------------------------------------

        pitched_sound = self.pitch_shift_sound(
            sound,
            pitch
        )

        # ----------------------------------------------
        # Cache
        # ----------------------------------------------

        self.pitched_sound_cache[
            cache_key
        ] = pitched_sound

        return pitched_sound
    def play_sfx_pitched(
        self,
        sound_path,
        pitch=1.0,
        volume=1.0,
        loops=0,
    ):
        sound = self.get_pitched_sound(
            sound_path,
            pitch
        )

        sound.set_volume(
            max(
                0.0,
                min(
                    1.0,
                    float(volume)
                )
            )
        )

        return sound.play(
            loops=loops
        )