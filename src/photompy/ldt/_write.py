"""
Internal LDT write helpers.

This module contains helper functions for writing LDT (EULUMDAT) files.
These are internal implementation details, not part of the public API.
"""

import numpy as np
from .header import LDTHeader
from ._read import convert_candela_to_ldt


def format_ldt_header(header: LDTHeader) -> str:
    """
    Format LDT header as string for file output.

    Args:
        header: LDTHeader instance

    Returns:
        Formatted header string with newlines
    """
    lines = [
        header.manufacturer,
        str(header.luminaire_type),
        str(header.symmetry),
        str(header.mc),
        str(header.dc),
        str(header.ng),
        str(header.dg),
        header.report_number,
        header.luminaire_name,
        header.luminaire_number,
        header.filename,
        header.date_user,
        str(header.length),
        str(header.width),
        str(header.height),
        str(header.luminous_length),
        str(header.luminous_width),
        str(header.luminous_height_c0),
        str(header.luminous_height_c90),
        str(header.luminous_height_c180),
        str(header.luminous_height_c270),
        str(header.dff),
        str(header.lorl),
        str(header.conversion_factor),
        str(header.tilt),
        str(header.num_lamp_sets),
    ]

    # Add lamp sets
    for lamp in header.lamps:
        lines.append(str(lamp.num_lamps))
        lines.append(lamp.lamp_type)
        lines.append(str(lamp.total_flux))

    return '\n'.join(lines) + '\n'


def format_ldt_angles(
    phis: np.ndarray,
    thetas: np.ndarray,
    precision: int = 2,
) -> str:
    """
    Format C-angles and G-angles for LDT output.

    In LDT format:
    - phis are C-angles (one per line)
    - thetas are G-angles (one per line)

    Args:
        phis: Horizontal angles (C-planes)
        thetas: Vertical angles (G/gamma)
        precision: Decimal places for floating point values

    Returns:
        Formatted string with angles, one per line
    """
    lines = []

    # C-angles (phis)
    for phi in phis:
        lines.append(f"{phi:.{precision}f}")

    # G-angles (thetas)
    for theta in thetas:
        lines.append(f"{theta:.{precision}f}")

    return '\n'.join(lines) + '\n'


def format_ldt_values(
    values: np.ndarray,
    total_flux: float,
    precision: int = 2,
) -> str:
    """
    Format intensity values for LDT output.

    Converts absolute candela to cd/klm and formats one value per line,
    organized by C-plane then G-angle.

    Args:
        values: Intensity values in candela, shape (num_phis, num_thetas)
        total_flux: Total luminous flux in lumens
        precision: Decimal places for values

    Returns:
        Formatted string with values, one per line
    """
    # Convert to cd/klm
    cdklm = convert_candela_to_ldt(values, total_flux)

    lines = []
    # Output order: for each C-plane, all G-angles
    for c_idx in range(cdklm.shape[0]):
        for g_idx in range(cdklm.shape[1]):
            lines.append(f"{cdklm[c_idx, g_idx]:.{precision}f}")

    return '\n'.join(lines) + '\n'


def prepare_photometry_for_ldt(
    photometry,
    which: str = "orig",
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    """
    Prepare photometry data for LDT output.

    Based on the symmetry of the photometry, determines the appropriate
    Isym value and potentially reduces the angle coverage.

    Args:
        photometry: Photometry object
        which: "orig" for original data, "full" for expanded

    Returns:
        Tuple of (phis, thetas, values, isym)
    """
    from ..photometry import LampSymmetry

    # Preserve original symmetry before potential expansion
    original_symmetry = photometry.symmetry

    if which == "full":
        phot = photometry.expanded()
    else:
        phot = photometry

    phis = phot.phis.copy()
    thetas = phot.thetas.copy()
    values = phot.values.copy()

    # Determine Isym from original symmetry (not expanded, which may be UNKNOWN)
    # When writing "full" data, we've already expanded so use Isym=0 (no symmetry)
    if which == "full":
        isym = 0  # Full expansion means no symmetry in output
    elif original_symmetry == LampSymmetry.AXIAL:
        isym = 1
    elif original_symmetry == LampSymmetry.HALF:
        isym = 2
    elif original_symmetry == LampSymmetry.QUAD:
        isym = 4
    elif original_symmetry == LampSymmetry.NONE:
        isym = 0
    else:
        isym = 0

    return phis, thetas, values, isym
