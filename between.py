"""Python port of DELTARUNE's gml_GlobalScript_between."""


def between(value=50, lower=0, upper=99999):
    """Return True only when lower < value < upper (exclusive bounds)."""
    return lower < value < upper
