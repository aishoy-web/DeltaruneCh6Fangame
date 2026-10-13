"""Battle entry and overworld-to-battle transition for the Chapter 6 fangame.

Ports:
* gml_GlobalScript_scr_battle
* obj_encounterbasic: Create and Step events
* obj_doom: Create and Alarm[0]

This is an engine-independent *entry controller*, not the combat/turn system.
Game supplies a prepared enemy layout and, ideally, a party layout. Game also
binds callbacks to its actual Tkinter renderer, sound player and world objects.
The transition runs on a 60-frame-per-second clock, as in the GML scripts.
"""

from __future__ import annotations

from collections.abc import Callable, MutableMapping, MutableSequence, Sequence
from dataclasses import dataclass, field
import math


MAX_ENEMY_SLOTS = 3
ENTRANCE_FRAMES = 20
PARTY_RUSH_FRAMES = 10
PARTY_POSE_FRAMES = 15  # Includes the GML frame that starts fightcon == 2.
DEFAULT_DOOM_ALARM = 25
SHINOBEETLE_DOOM_ALARM = 24
FLAG_BATTLE = 9


@dataclass(slots=True)
class EnemySpawn:
    """One global.monster* slot; monster_type=0 represents an empty slot."""

    monster_type: int
    x: float
    y: float
    sprite: str


@dataclass(slots=True)
class EnemyMarker:
    """Enemy's scr_dark_marker, including a timed linear entry animation."""

    x: float
    y: float
    sprite: str
    depth: int = 0
    enemy_slot: int = -1
    scale_x: float = 1.0
    scale_y: float = 1.0
    alive: bool = True

    _start_x: float = field(default=0.0, init=False, repr=False)
    _start_y: float = field(default=0.0, init=False, repr=False)
    _end_x: float = field(default=0.0, init=False, repr=False)
    _end_y: float = field(default=0.0, init=False, repr=False)
    _duration: float = field(default=0.0, init=False, repr=False)
    _elapsed: float = field(default=0.0, init=False, repr=False)

    def move_to_over_frames(self, x: float, y: float, frames: float = ENTRANCE_FRAMES) -> None:
        if frames < 0:
            raise ValueError("frames cannot be negative")
        self._start_x, self._start_y = self.x, self.y
        self._end_x, self._end_y = x, y
        self._duration = frames
        self._elapsed = 0.0
        if frames == 0:
            self.x, self.y = x, y

    @property
    def moving(self) -> bool:
        return self.alive and self._elapsed < self._duration

    def update(self, frames: float = 1.0) -> None:
        if not self.alive or not self.moving:
            return
        self._elapsed = min(self._duration, self._elapsed + frames)
        blend = self._elapsed / self._duration
        self.x = self._start_x + (self._end_x - self._start_x) * blend
        self.y = self._start_y + (self._end_y - self._start_y) * blend


@dataclass(slots=True)
class DoomEffect:
    """obj_doom: after alarm[0], destroy both the target marker and itself."""

    target: EnemyMarker
    x: float
    y: float
    remaining_frames: float
    respects_platmode: bool = False
    triggered: bool = False
    alive: bool = True

    def update(self, frames: float = 1.0) -> bool:
        """Return True only on the frame the effect destroys its target."""
        if self.triggered:
            return False
        self.remaining_frames = max(0.0, self.remaining_frames - frames)
        if self.remaining_frames == 0:
            self.triggered = True
            self.target.alive = False
            self.alive = False
            return True
        return False


@dataclass(slots=True)
class PartySpawn:
    """One member of global.char[] and global.heromake*[] (in party order).

    x/y: overworld coordinates, or follower instance coordinates.
    battle_x/y: destination supplied by scr_encountersetup.
    overworld_sprite: global.cinstance[i].rsprite for followers; Kris uses
        spr_kris_sword_jump_down regardless of this field.
    armed: false corresponds to global.charweapon[2] == 0 for Susie.
    sideb_phase: only matters for the *first* follower when they are Noelle.
    """

    character_id: int  # 1=Kris, 2=Susie, 3=Ralsei, 4=Noelle
    x: float
    y: float
    battle_x: float
    battle_y: float
    overworld_sprite: str = ""
    name: str = ""
    armed: bool = True
    sideb_phase: int = 0


@dataclass(slots=True)
class PartyMarker:
    """Transient obj_encounterbasic.c[i] marker (not a persistent party actor)."""

    party_index: int
    character_id: int
    x: float
    y: float
    target_x: float
    target_y: float
    sprite: str
    depth: int
    image_alpha: float = 1.0
    image_index: float = 0.0
    image_speed: float = 1.0
    alive: bool = True
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    in_pose: bool = False
    _alpha_target: float = field(default=1.0, init=False, repr=False)
    _alpha_frames: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        self.velocity_x = (self.target_x - self.x) / PARTY_RUSH_FRAMES
        self.velocity_y = (self.target_y - self.y) / PARTY_RUSH_FRAMES

    def begin_alpha_lerp(self, target: float = 1.0, frames: int = 10) -> None:
        """Linearly fade image_alpha to target, as in scr_lerpvar."""
        self._alpha_target = target
        if frames <= 0:
            self.image_alpha = target
            self._alpha_frames = 0
        else:
            self._alpha_frames = frames

    def step(self) -> None:
        if not self.alive:
            return
        self.x += self.velocity_x
        self.y += self.velocity_y
        # GML automatically advances image_index by image_speed each frame.
        # The renderer should wrap the index using its own sprite frame count.
        self.image_index += self.image_speed
        if self._alpha_frames:
            self.image_alpha += (self._alpha_target - self.image_alpha) / self._alpha_frames
            self._alpha_frames -= 1
            if not self._alpha_frames:
                self.image_alpha = self._alpha_target


@dataclass(slots=True)
class BattleState:
    encounter_no: int
    special_battle: int
    chapter: int = 6
    music_to_load: str | None = None
    fade_overworld_music: bool = False
    interact: int = 2
    overworld_suspended: bool = True
    platform_paused: bool = True
    markers: list[EnemyMarker | None] = field(
        default_factory=lambda: [None] * MAX_ENEMY_SLOTS
    )
    doom_effects: list[DoomEffect] = field(default_factory=list)
    party_markers: list[PartyMarker] = field(default_factory=list)
    fightcon: int = 1                 # 1 = rush, 2 = pose, 3 = handoff
    counttimer: int = 0
    elapsed_frames: int = 0
    controller_started: bool = False
    intro_complete: bool = False      # Handoff AND enemy marker cleanup finished.
    overworld_song_paused: bool = False


BattleCallback = Callable[[BattleState], None]
DoomCallback = Callable[[DoomEffect, BattleState], None]
PartyCallback = Callable[[PartyMarker, BattleState], None]
MusicFadeCallback = Callable[[BattleState, int], None]
SoundCallback = Callable[[str, float, BattleState], None]


class BattleController:
    """Entry coordinator. Bind callbacks to the Game instance's own systems.

    on_encounter_setup is where Game calls/ports scr_encountersetup and prepares
    monster/hero positions. Supply its *result* via enemy_slots/party_members;
    this module does not invent encounter definitions or screen coordinates.

    on_suspend_overworld should hide mainchara, followers and platform actors,
    freeze climb_kris, pause the platform game, and reset relevant actor flags.
    (The provided Game architecture is needed to perform these operations.)

    on_start can create/show the battle background and begin rendering markers.
    on_controller_start is the replacement for instance_create(obj_battlecontroller).
    on_intro_complete fires after handoff AND all obj_doom alarms have fired.
    """

    def __init__(
        self,
        *,
        on_start: BattleCallback | None = None,
        on_doom_alarm: DoomCallback | None = None,
        on_intro_complete: BattleCallback | None = None,
        on_encounter_setup: BattleCallback | None = None,
        on_suspend_overworld: BattleCallback | None = None,
        on_music_fade: MusicFadeCallback | None = None,
        on_music_pause: BattleCallback | None = None,
        on_afterimage: PartyCallback | None = None,
        on_sound: SoundCallback | None = None,
        on_controller_start: BattleCallback | None = None,
    ) -> None:
        self.state: BattleState | None = None
        self.music: str | None = None
        self.on_start = on_start
        self.on_doom_alarm = on_doom_alarm
        self.on_intro_complete = on_intro_complete
        self.on_encounter_setup = on_encounter_setup
        self.on_suspend_overworld = on_suspend_overworld
        self.on_music_fade = on_music_fade
        self.on_music_pause = on_music_pause
        self.on_afterimage = on_afterimage
        self.on_sound = on_sound
        self.on_controller_start = on_controller_start
        self._fractional_frames = 0.0
        self._party_spawns: Sequence[PartySpawn] = ()
        self._chapter5_flag_1311 = False

    def start_battle(
        self,
        encounter_no: int,
        special_battle: int,
        enemy_slots: Sequence[EnemySpawn | None],
        flags: MutableSequence[int] | MutableMapping[int, int],
        *,
        chapter: int = 6,
        existing_markers: Sequence[EnemyMarker | None] = (),
        room_id: str | None = None,
        default_music: str = "battle.ogg",
        party_members: Sequence[PartySpawn] = (),
        kris_platform_origin: tuple[float, float] | None = None,
        kris_climb_origin: tuple[float, float] | None = None,
        chapter5_flag_1311: bool = False,
    ) -> BattleState:
        """Launch an encounter with the prepared party and monster layout.

        Existing use sites without party_members remain supported, but a real
        overworld entry should supply at least Kris with its actual coordinates.
        `kris_climb_origin` overrides platform/Kris origins if both are supplied.
        Each enemy slot corresponds to one of the three GML monster slots.
        """
        if self.state is not None:
            raise RuntimeError("A battle is already active; call end_battle() first")
        if len(party_members) > 3:
            raise ValueError("GML encounterbasic supports up to three party markers")

        current_flag = _get_flag(flags, FLAG_BATTLE)
        music_to_load: str | None = None
        if current_flag != 2:
            _set_flag(flags, FLAG_BATTLE, 1)
            music_to_load = (
                "rakuichi_buster_wip.ogg" if chapter == 5 else default_music
            )
            self.music = music_to_load

        state = BattleState(
            encounter_no=encounter_no,
            special_battle=special_battle,
            chapter=chapter,
            music_to_load=music_to_load,
            fade_overworld_music=_get_flag(flags, FLAG_BATTLE) == 1,
        )
        self.state = state
        self._fractional_frames = 0.0
        self._party_spawns = tuple(party_members)
        self._chapter5_flag_1311 = chapter5_flag_1311

        # obj_encounterbasic Create: set interact, fade the current world song,
        # run encountersetup, and hide/freeze the overworld actors.
        if state.fade_overworld_music and self.on_music_fade is not None:
            self.on_music_fade(state, 20)
        if self.on_encounter_setup is not None:
            self.on_encounter_setup(state)
        if self.on_suspend_overworld is not None:
            self.on_suspend_overworld(state)

        for index, member in enumerate(party_members):
            x, y = member.x, member.y
            if index == 0 and member.character_id == 1:
                if kris_platform_origin is not None:
                    x, y = kris_platform_origin
                if kris_climb_origin is not None:
                    x, y = kris_climb_origin
            elif kris_climb_origin is not None:
                # In climbing mode GML creates follower markers at Kris's
                # climbing position with alpha 0.
                x, y = kris_climb_origin

            if index == 0 and member.character_id == 1:
                sprite = "spr_kris_sword_jump_down"
            else:
                sprite = member.overworld_sprite
                if sprite == "spr_susier_dark":
                    sprite = "spr_susier_wall"
                if member.name.lower() == "noelle":
                    sprite = "spr_noelleb_battleintro"
                    if index == 1 and member.sideb_phase >= 2:
                        sprite = "spr_noelleb_battleintro_sideb"

            marker = PartyMarker(
                party_index=index,
                character_id=member.character_id,
                x=x,
                y=y,
                target_x=member.battle_x,
                target_y=member.battle_y,
                sprite=sprite,
                depth=200 - index * 20,
                image_alpha=(0.0 if index > 0 and kris_climb_origin is not None else 1.0),
                image_speed=(0.5 if member.name.lower() == "noelle" and index > 0 else 1.0),
            )
            if encounter_no == 230 and index == 0:
                # Original special encounter removes Kris's marker immediately.
                marker.alive = False
            state.party_markers.append(marker)

        for slot in range(MAX_ENEMY_SLOTS):
            enemy = enemy_slots[slot] if slot < len(enemy_slots) else None
            if enemy is None or enemy.monster_type == 0:
                continue
            supplied = existing_markers[slot] if slot < len(existing_markers) else None
            if supplied is not None and supplied.alive:
                marker = supplied
            else:
                marker = EnemyMarker(
                    x=enemy.x + 300, y=enemy.y, sprite=enemy.sprite, depth=-slot
                )
            marker.enemy_slot = slot
            marker.move_to_over_frames(enemy.x, enemy.y, ENTRANCE_FRAMES)
            if (chapter == 5 and room_id == "room_dw_cliff_kawkawdash"
                    and marker.sprite == "spr_kawkaw"):
                marker.scale_x = 1.5
                marker.scale_y = 1.5
            alarm = (SHINOBEETLE_DOOM_ALARM
                     if marker.sprite in {"spr_shinobeetle", "spr_shinobeetle_pose"}
                     else DEFAULT_DOOM_ALARM)
            state.markers[slot] = marker
            state.doom_effects.append(DoomEffect(
                target=marker, x=marker.x, y=marker.y,
                remaining_frames=alarm, respects_platmode=False,
            ))

        if self.on_start is not None:
            self.on_start(state)
        return state

    def _switch_to_pose(self, state: BattleState) -> None:
        if state.encounter_no not in (84, 230) and self.on_sound is not None:
            self.on_sound("snd_impact", 0.7, state)
            self.on_sound("snd_weaponpull_fast", 0.8, state)

        if state.encounter_no == 230:
            # The GML code doesn't stop movement or switch poses for 230.
            return
        for marker in state.party_markers:
            if not marker.alive:
                continue
            marker.velocity_x = marker.velocity_y = 0.0
            member = self._party_spawns[marker.party_index]
            if marker.character_id != 4:  # Noelle keeps her image frame.
                marker.image_index = 0.0
            if marker.character_id == 1:
                marker.sprite = "spr_krisb_attack"
            elif marker.character_id == 2:
                marker.sprite = ("spr_susieb_attack" if member.armed
                                 else "spr_susieb_attack_unarmed")
            elif marker.character_id == 3:
                marker.sprite = "spr_ralsei_battleintro"
                if state.chapter == 5 and state.encounter_no == 225:
                    marker.sprite = "spr_ralsei_begin_battle_serious"
                if state.chapter == 5 and self._chapter5_flag_1311:
                    marker.sprite = "spr_ralseib_battleintro"
            marker.image_speed = 0.5
            marker.in_pose = True
            marker.begin_alpha_lerp(1.0, 10)

    def _advance_one_frame(self, state: BattleState) -> None:
        state.elapsed_frames += 1

        # Enemy marker animations and obj_doom Alarm[0] are independent of the
        # party transition, and continue after obj_encounterbasic is destroyed.
        for marker in state.markers:
            if marker is not None:
                marker.update()
        for doom in state.doom_effects:
            if doom.update() and self.on_doom_alarm is not None:
                self.on_doom_alarm(doom, state)

        if state.fightcon == 1:
            # GML calls snd_pause every Step in phase 1. Pausing only once
            # has the same observable audio result and avoids duplicate calls.
            if state.fade_overworld_music and not state.overworld_song_paused:
                state.overworld_song_paused = True
                if self.on_music_pause is not None:
                    self.on_music_pause(state)
            state.counttimer += 1
            for marker in state.party_markers:
                marker.step()
            if state.counttimer < PARTY_RUSH_FRAMES:
                if self.on_afterimage is not None:
                    for marker in state.party_markers:
                        if marker.alive:
                            self.on_afterimage(marker, state)
            else:
                self._switch_to_pose(state)
                state.fightcon = 2
                state.counttimer = 0

        # Deliberately NOT 'elif': in GML both fightcon == 1 and == 2 checks
        # happen on the same Step. Phase 2 starts counting on rush frame 10.
        if state.fightcon == 2:
            state.counttimer += 1
            if state.elapsed_frames > PARTY_RUSH_FRAMES:
                for marker in state.party_markers:
                    marker.step()
            if state.counttimer >= PARTY_POSE_FRAMES:
                state.counttimer = 0
                state.fightcon = 3
                for marker in state.party_markers:
                    marker.alive = False
                state.controller_started = True
                if self.on_controller_start is not None:
                    self.on_controller_start(state)

        if (state.controller_started and not state.intro_complete
                and all(doom.triggered for doom in state.doom_effects)):
            state.intro_complete = True
            if self.on_intro_complete is not None:
                self.on_intro_complete(state)

    def update(self, frames: float = 1.0) -> None:
        """Advance by game frames (call once per frame, or dt_seconds*60).

        Fractional frame amounts accumulate so one-shot sound/animation
        events always fire at the correct *integer* frame boundary.
        """
        if not math.isfinite(frames) or frames < 0:
            raise ValueError("frames must be finite and non-negative")
        state = self.state
        if state is None or state.intro_complete:
            return
        self._fractional_frames += frames
        steps = int(self._fractional_frames)
        self._fractional_frames -= steps
        for _ in range(steps):
            if state.intro_complete or self.state is not state:
                break
            self._advance_one_frame(state)

    def end_battle(self) -> None:
        """Dispose entry state. Battle outcome/world restoration comes later."""
        self.state = None
        self._party_spawns = ()
        self._fractional_frames = 0.0

def _get_flag(flags: MutableSequence[int] | MutableMapping[int, int], key: int) -> int:
    if isinstance(flags, MutableMapping):
        return flags.get(key, 0)
    return flags[key] if key < len(flags) else 0


def _set_flag(flags: MutableSequence[int] | MutableMapping[int, int], key: int, value: int) -> None:
    if isinstance(flags, MutableMapping):
        flags[key] = value
    else:
        if len(flags) <= key:
            flags.extend([0] * (key + 1 - len(flags)))
        flags[key] = value
