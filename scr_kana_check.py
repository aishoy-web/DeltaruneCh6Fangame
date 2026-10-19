"""Python port of gml_GlobalScript_scr_kana_check."""


def scr_kana_check(text: str) -> int:
    """Return 1 if any character has a Unicode value >= 12352; otherwise 0.

    This deliberately follows the original GML comparison, rather than
    checking only the Japanese hiragana or katakana Unicode blocks.
    """
    for char in text:
        if ord(char) >= 12352:
            return 1
    return 0
