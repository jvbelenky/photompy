# Modern API (recommended)
from .ies import IESFile
from .ldt import LDTFile
from .photometry import Photometry, PhotometricType
from .tilt import TiltData, LampGeometry
from .ies_header import FileGeneration, Units, IESVersion
from .geometry import LuminousOpening, LuminousShape
from .create import create_ies, create_ldt

# Deprecated functions (emit warnings when used)
from .legacy import (
    read_ies_data,
    write_ies_data,
    scale_lamp_to_max,
    scale_lamp_to_total,
    total_optical_power,
    lamp_area,
    interpolate_values,
    get_intensity,
    plot_ies,
)

# Helper functions (still public for backward compatibility)
from ._plot import (
    get_coords,
    polar_to_cartesian,
    plot_valdict_cartesian,
    plot_valdict_polar,
)

__all__ = [
    # Modern API
    "IESFile",
    "LDTFile",
    "Photometry",
    "PhotometricType",
    "TiltData",
    "LampGeometry",
    "FileGeneration",
    "Units",
    "IESVersion",
    "LuminousOpening",
    "LuminousShape",
    # File creation functions
    "create_ies",
    "create_ldt",
    # Deprecated (will emit warnings)
    "read_ies_data",
    "write_ies_data",
    "scale_lamp_to_max",
    "scale_lamp_to_total",
    "total_optical_power",
    "lamp_area",
    "interpolate_values",
    "get_intensity",
    "plot_ies",
    # Helper functions
    "get_coords",
    "polar_to_cartesian",
    "plot_valdict_cartesian",
    "plot_valdict_polar",
]
