# Modern API (recommended)
from .ies import IESFile
from .ldt import LDTFile
from .photometry import Photometry, PhotometricType
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

__all__ = [
    # Modern API
    "IESFile",
    "LDTFile",
    "Photometry",
    "PhotometricType",
    "create_ies",
    "create_ldt",
    # Deprecated (emit warnings)
    "read_ies_data",
    "write_ies_data",
    "scale_lamp_to_max",
    "scale_lamp_to_total",
    "total_optical_power",
    "lamp_area",
    "interpolate_values",
    "get_intensity",
    "plot_ies",
]
