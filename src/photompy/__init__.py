# Modern API (recommended)
from .ies import IESFile
from .photometry import Photometry
from .tilt import TiltData, LampGeometry
from .ies_header import FileGeneration

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
    "Photometry",
    "TiltData",
    "LampGeometry",
    "FileGeneration",
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
