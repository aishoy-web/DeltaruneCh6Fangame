from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class StartupMode(Enum):
    NEW_GAME = "new_game"
    IMPORT_CHAPTER5 = "import_chapter5"
    CONTINUE_CHAPTER6 = "continue_chapter6"


@dataclass
class StartupResult:
    mode: StartupMode
    available_slots: list[int]


def resolve_startup() -> StartupResult:
    """
    Determine how Chapter 6 should begin.

    This function only resolves the startup situation.
    It does not start the game or import save data itself.
    """

    # Chapter 6 save detection will be added here later.
    chapter6_slots = []

    if chapter6_slots:
        return StartupResult(
            mode=StartupMode.CONTINUE_CHAPTER6,
            available_slots=chapter6_slots,
        )

    chapter5_slots = find_chapter5_completion_slots()

    if chapter5_slots:
        return StartupResult(
            mode=StartupMode.IMPORT_CHAPTER5,
            available_slots=chapter5_slots,
        )

    return StartupResult(
        mode=StartupMode.NEW_GAME,
        available_slots=[],
    )


def find_chapter5_completion_slots() -> list[int]:
    """
    Find official DELTARUNE Chapter 5 completion files.

    DELTARUNE stores completed versions of save slots 0-2
    as filech5_3, filech5_4, and filech5_5.
    """

    save_dir = get_deltarune_save_directory()

    slots = []

    for slot in range(3):
        completion_file = save_dir / f"filech5_{slot + 3}"

        if completion_file.is_file():
            slots.append(slot)

    return slots


def get_deltarune_save_directory() -> Path:
    """
    Return the official DELTARUNE save directory.
    """

    return (
        Path.home()
        / "AppData"
        / "Local"
        / "DELTARUNE"
    )