class IESBaseError(Exception):
    """Anything fatally wrong with an IES/LDT."""


class IESPathError(IESBaseError):
    """File name / extension mismatch, unreadable."""


class IESDecodeError(IESBaseError):
    """Could not decode bytes → str cleanly."""


class IESHeaderError(IESBaseError):
    """Missing TILT= line, numeric row too short…"""


class IESDataError(IESBaseError):
    """Angles or candela counts contradict header."""
