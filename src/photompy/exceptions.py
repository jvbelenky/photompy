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


# LDT (EULUMDAT) specific exceptions
class LDTBaseError(Exception):
    """Anything fatally wrong with an LDT file."""


class LDTPathError(LDTBaseError):
    """File name / extension mismatch, unreadable."""


class LDTHeaderError(LDTBaseError):
    """Header line missing or malformed."""


class LDTDataError(LDTBaseError):
    """Angles or candela counts contradict header."""
