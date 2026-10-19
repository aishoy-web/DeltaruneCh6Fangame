"""Chapter 6 fangame adaptation of DELTARUNE's gml_GlobalScript_scr_credit.

Exports the original GML names:
    scr_credit(header, text_line, columns=1)
    generate_credits(team_credits=None)

The `scr_credit` constructor retains the original three attributes exactly.
`generate_credits` intentionally uses a SHORT, TWO-PAGE default instead of
copying Chapter 5's full 16-page credits; crediting the original DELTARUNE
creators does not imply that they worked on this fangame.

Each page is a list of `scr_credit` entries, and the entire credits sequence
is a list of pages -- the same nested structure as the supplied GML script.
The calling credits renderer controls typography, display times, and layout.
"""

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass
class scr_credit:
    """Literal port of GML's `scr_credit` constructor.

    `header` and `text_line` are generally lists of strings, but may also
    contain nested lists; the supplied GML generator uses both forms.
    `columns` is stored for the eventual credits renderer to interpret.
    """

    header: Any
    text_line: Any
    columns: int = 1


# Optional Python-style alias; existing code can import `scr_credit` directly.
CreditEntry = scr_credit


# Edit the names here, or pass a different mapping to generate_credits().
# Empty categories are hidden until someone needs to be credited for them.
DEFAULT_TEAM_CREDITS: dict[str, tuple[str, ...]] = {
    "Project Direction & Programming": ("[Your credited name]",),
    "Writing & Design": (),
    "Art & Animation": (),
    "Music & Sound": (),
    "Testing & Additional Help": (),
}


def _credit_heading(role: str) -> str:
    """Apply the hyphenated heading style found in the GML source."""
    role = str(role)
    return role if role.startswith("-") and role.endswith("-") else f"-{role}-"


def generate_credits(
    team_credits: Mapping[str, Sequence[Any] | str] | None = None,
) -> list[list[scr_credit]]:
    """Build concise Chapter 6 fangame credits.

    Args:
        team_credits: Insertion-ordered role -> names mapping for people who
            ACTUALLY worked on this fangame. Strings are treated as one name.
            Omitted or empty roles do not appear. If None, use the editable
            DEFAULT_TEAM_CREDITS (with clearly labeled placeholder names).

    Returns:
        A list of pages; each page is a list of `scr_credit` objects.
        Normally page 1 is the fangame team and page 2 credits the original
        DELTARUNE creators with a non-affiliation notice. If team_credits is
        empty, only the original-game acknowledgment page is returned.

    Notes:
        - This is a Chapter 6 adaptation, not a transcript of Chapter 5's
          names or localization string IDs.
        - Render-time translation and page timing belong to the host game.
    """
    if team_credits is None:
        team_credits = DEFAULT_TEAM_CREDITS

    fangame_page: list[scr_credit] = []
    for role, names in team_credits.items():
        if isinstance(names, str):
            lines = [names]
        else:
            lines = list(names)
        if not lines:
            continue
        fangame_page.append(scr_credit([_credit_heading(role)], lines))

    original_game_page = [
        scr_credit(["-Original Game-"], ["DELTARUNE", "Created by Toby Fox"]),
        scr_credit(["-Original Artwork-"], ["Temmie Chang"]),
        scr_credit(["-Original Development-"], ["The DELTARUNE development team"]),
        scr_credit(
            ["-Fan Project Notice-"],
            ["An unofficial fan project; not affiliated with or endorsed by the original creators."],
        ),
    ]

    pages = [fangame_page] if fangame_page else []
    pages.append(original_game_page)
    return pages


__all__ = [
    "scr_credit",
    "CreditEntry",
    "DEFAULT_TEAM_CREDITS",
    "generate_credits",
]
