from configparser import ConfigParser
from pathlib import Path
import os
import shutil


BASE_DIR = Path(__file__).resolve().parent


class ProgressTracker:
    """
    Shared DELTARUNE / fangame chapter progress manager.

    Official Chapters 1-5 are read from the normal
    DELTARUNE save directory when available.

    Fangame Chapter 6 data is kept separately so we do
    not overwrite official DELTARUNE files.
    """

    def __init__(self):

        # --------------------------------------------------
        # Official DELTARUNE save directory
        # --------------------------------------------------

        local_appdata = os.environ.get(
            "LOCALAPPDATA"
        )

        if local_appdata:

            self.official_dir = (
                Path(local_appdata)
                / "DELTARUNE"
            )

        else:

            self.official_dir = None

        # --------------------------------------------------
        # Fangame-owned save directory
        # --------------------------------------------------

        self.fangame_dir = (
            BASE_DIR
            / "save_data"
        )

        self.fangame_dir.mkdir(
            parents=True,
            exist_ok=True
        )

    # ======================================================
    # FILE PATHS
    # ======================================================

    def _read_directories(self, chapter):

        """
        Chapters 1-5 prefer official DELTARUNE data.

        Chapter 6 belongs to this fangame and therefore
        only uses our fangame save directory.
        """

        directories = []

        if (
            chapter <= 5
            and self.official_dir is not None
            and self.official_dir.exists()
        ):
            directories.append(
                self.official_dir
            )

        directories.append(
            self.fangame_dir
        )

        return directories

    def _file_exists(self, chapter, filename):

        for directory in self._read_directories(
            chapter
        ):

            if (directory / filename).exists():
                return True

        return False

    def current_save_path(
        self,
        chapter,
        slot
    ):

        self._validate_slot(slot)

        return (
            self.fangame_dir
            / f"filech{chapter}_{slot}"
        )

    def completed_save_path(
        self,
        chapter,
        slot
    ):

        self._validate_slot(slot)

        return (
            self.fangame_dir
            / f"filech{chapter}_{slot + 3}"
        )

    @staticmethod
    def _validate_slot(slot):

        if slot not in (0, 1, 2):

            raise ValueError(
                "Save slot must be 0, 1, or 2."
            )

    # def debug_official_ini(self):
    #     if self.official_dir is None:
    #         # print("No official DELTARUNE directory.")
    #         return

    #     ini_path = (
    #         self.official_dir
    #         / "dr.ini"
    #     )

    #     print(
    #         "dr.ini path:",
    #         ini_path
    #     )

    #     print(
    #         "dr.ini exists:",
    #         ini_path.exists()
    #     )

    #     if not ini_path.exists():
    #         return

    #     parser = ConfigParser(
    #         interpolation=None
    #     )

    #     parser.optionxform = str

    #     parser.read(
    #         ini_path,
    #         encoding="utf-8"
    #     )

    #     print(
    #         "dr.ini sections:",
    #         parser.sections()
    #     )

    #     if parser.has_section(
    #         "URA"
    #     ):

    #         print(
    #             "URA contents:",
    #             dict(
    #                 parser.items(
    #                     "URA"
    #                 )
    #             )
    #         )

    #     else:

    #         print(
    #             "No [URA] section exists."
    #         )

    # ======================================================
    # CURRENT SAVE FILES
    # ======================================================

    def chapter_save_file_exists(
        self,
        chapter
    ):

        # Python translation of:
        # scr_chapter_save_file_exists()

        for slot in range(3):

            if self.chapter_save_file_exists_in_slot(
                chapter,
                slot
            ):
                return True

        return False

    def chapter_save_file_exists_in_slot(
        self,
        chapter,
        slot
    ):

        self._validate_slot(slot)

        filename = (
            f"filech{chapter}_{slot}"
        )

        return self._file_exists(
            chapter,
            filename
        )

    # ======================================================
    # COMPLETED CHAPTER FILES
    # ======================================================

    def completed_chapter_any_slot(
        self,
        chapter
    ):

        # Python translation of:
        # scr_completed_chapter_any_slot()

        for slot in range(3):

            if self.completed_chapter_in_slot(
                chapter,
                slot
            ):
                return True

        return False

    def completed_chapter_in_slot(
        self,
        chapter,
        slot
    ):

        self._validate_slot(slot)

        filename = (
            f"filech{chapter}_{slot + 3}"
        )

        return self._file_exists(
            chapter,
            filename
        )

    def completion_slots(
        self,
        chapter
    ):

        """
        Mirrors the _completed_files logic from
        obj_ui_chapter.

        0 = not completed
        1 = completed, current save still exists
        2 = completed, current save no longer exists
        """

        result = []

        for slot in range(3):

            completed = (
                self.completed_chapter_in_slot(
                    chapter,
                    slot
                )
            )

            if not completed:

                result.append(0)
                continue

            current_exists = (
                self.chapter_save_file_exists_in_slot(
                    chapter,
                    slot
                )
            )

            if current_exists:
                result.append(1)
            else:
                result.append(2)

        return result

    # ======================================================
    # CHAPTER REVEAL
    # ======================================================

    def is_chapter_revealed(
        self,
        chapter
    ):

        if chapter == 1:
            return True

        completed_previous = (
            self.completed_chapter_any_slot(
                chapter - 1
            )
        )

        completed_current = (
            self.completed_chapter_any_slot(
                chapter
            )
        )

        in_progress = (
            self.chapter_save_file_exists(
                chapter
            )
        )

        return (
            completed_previous
            or completed_current
            or in_progress
        )

    def highest_revealed_chapter(
        self,
        maximum
    ):

        highest = 1

        for chapter in range(
            1,
            maximum + 1
        ):

            if not self.is_chapter_revealed(
                chapter
            ):
                break

            highest = chapter

        return highest

    # ======================================================
    # URA / SECRET BOSS DATA
    # ======================================================

    def _read_ini_value(
        self,
        ini_path,
        section,
        key,
        default=0
    ):

        if not ini_path.exists():
            return default

        parser = ConfigParser(
            interpolation=None
        )

        parser.optionxform = str

        try:

            parser.read(
                ini_path,
                encoding="utf-8"
            )

            if not parser.has_section(
                section
            ):
                return default

            value = parser.get(
                section,
                key,
                fallback=str(default)
            )

            # DELTARUNE's dr.ini stores numeric values
            # wrapped in quotes, for example:
            #
            #     "2.000000"
            #
            # Strip whitespace and surrounding quotes before
            # converting to a Python number.
            value = value.strip()
            value = value.strip('"')
            value = value.strip("'")

            return int(
                float(value)
            )

        except (
            OSError,
            ValueError
        ):
            return default

    def get_ura_value(
        self,
        chapter,
        slot
    ):

        self._validate_slot(slot)

        key = f"{chapter}_{slot}"

        # Chapters 1-5:
        # read official dr.ini first.
        if (
            chapter <= 5
            and self.official_dir is not None
        ):

            value = self._read_ini_value(
                self.official_dir / "dr.ini",
                "URA",
                key,
                0
            )

            if value != 0:
                return value

        # Fangame data.
        return self._read_ini_value(
            self.fangame_dir / "dr.ini",
            "URA",
            key,
            0
        )

    def set_ura_value(
        self,
        chapter,
        slot,
        value
    ):

        self._validate_slot(slot)

        ini_path = (
            self.fangame_dir
            / "dr.ini"
        )

        parser = ConfigParser(
            interpolation=None
        )

        parser.optionxform = str

        if ini_path.exists():

            parser.read(
                ini_path,
                encoding="utf-8"
            )

        if not parser.has_section(
            "URA"
        ):
            parser.add_section(
                "URA"
            )

        parser.set(
            "URA",
            f"{chapter}_{slot}",
            str(int(value))
        )

        with ini_path.open(
            "w",
            encoding="utf-8"
        ) as file:

            parser.write(file)

    def fought_secret_boss_any_slot(
        self,
        chapter
    ):

        # Python translation of:
        # scr_fought_secret_boss_any_slot()

        for slot in range(3):

            result = self.get_ura_value(
                chapter,
                slot
            )

            if result > 0:
                return True

        return False

    # ======================================================
    # FANGAME WRITES
    # ======================================================

    def mark_chapter_completed(
        self,
        chapter,
        slot
    ):

        """
        Creates the completed-slot equivalent:

            slot 0 -> filechX_3
            slot 1 -> filechX_4
            slot 2 -> filechX_5

        If a current fangame save exists, copy it so the
        completed file can later retain game-state data.
        """

        current = self.current_save_path(
            chapter,
            slot
        )

        completed = self.completed_save_path(
            chapter,
            slot
        )

        if current.exists():

            shutil.copy2(
                current,
                completed
            )

        else:

            completed.touch()
    def highest_shadow_crystal_chapter(
        self,
        maximum_chapter=5
    ):

        highest = 0

        for chapter in range(
            1,
            maximum_chapter + 1
        ):

            if self.fought_secret_boss_any_slot(
                chapter
            ):

                highest = chapter

        return highest
    def shadow_crystal_grid(
        self,
        maximum_chapter=6
    ):

        highest_chapter = 0

        # Equivalent to obj_ui_grid_Create_0.
        for chapter in range(
            1,
            maximum_chapter + 1
        ):

            if (
                self.fought_secret_boss_any_slot(
                    chapter
                )
                and chapter > highest_chapter
            ):
                highest_chapter = chapter

        grid = []

        for chapter in range(
            1,
            highest_chapter + 1
        ):

            grid.append(
                {
                    "chapter": chapter,
                    "results":
                        self.shadow_crystal_results(
                            chapter
                        )
                }
            )

        return grid
    def get_shadow_crystal_result(
        self,
        chapter,
        slot
    ):
        """
        Returns the URA result used by obj_ui_grid_line.

        This intentionally preserves the Chapter 3 special
        case from the original game:

            Chapter 3, URA result 2 -> display as 0
        """

        result = self.get_ura_value(
            chapter,
            slot
        )

        if (
            chapter == 3
            and result == 2
        ):
            result = 0

        return result
    def shadow_crystal_obtained(
        self,
        chapter,
        slot
    ):
        """
        Equivalent to the frame-selection logic in
        obj_ui_grid_line_Draw_0.
        """

        return (
            self.get_shadow_crystal_result(
                chapter,
                slot
            ) > 0
        )
    def shadow_crystal_results(
        self,
        chapter
    ):

        return [
            self.get_shadow_crystal_result(
                chapter,
                slot
            )
            for slot in range(3)
        ]