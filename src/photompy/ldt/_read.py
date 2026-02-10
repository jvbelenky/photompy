"""
Internal LDT read helpers.

This module contains helper functions for parsing LDT (EULUMDAT) files.
These are internal implementation details, not part of the public API.

EULUMDAT Format:
- Lines 1-26+ are fixed header data
- Following lines contain C-angles, G-angles, and intensity values
- Values are stored as cd/klm (candela per kilolumen)
"""

import numpy as np
from .header import LDTHeader
from ..exceptions import LDTHeaderError, LDTDataError


def parse_ldt_lines(content: str) -> list[str]:
    """
    Split LDT file content into lines.

    Args:
        content: Raw file content as string

    Returns:
        List of stripped lines
    """
    # LDT files can have various line endings
    lines = content.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    return [line.strip() for line in lines]


def parse_ldt_header(lines: list[str], strict: bool = True) -> tuple[LDTHeader, int]:
    """
    Parse LDT header from lines.

    Args:
        lines: List of stripped file lines
        strict: If True, raise errors on malformed data

    Returns:
        Tuple of (LDTHeader, data_start_index)
    """
    # from_lines now returns (header, data_start_idx) directly
    return LDTHeader.from_lines(lines, strict=strict)


def parse_ldt_angles(
    lines: list[str],
    start_idx: int,
    mc: int,
    ng: int,
    isym: int,
    strict: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Parse C-angles, G-angles, and candela values from LDT data lines.

    Args:
        lines: List of file lines
        start_idx: Index where angle data starts
        mc: Number of C-planes (from header)
        ng: Number of G-angles (from header)
        isym: Symmetry type (0-4)
        strict: If True, raise errors on malformed data

    Returns:
        Tuple of (c_angles, g_angles, values) where values has shape (mc, ng)
    """
    idx = start_idx

    # Determine actual number of C-planes based on symmetry
    if isym == 0:
        # No symmetry: mc planes from 0 to 360
        num_c_planes = mc
    elif isym == 1:
        # Axially symmetric: single C-plane
        num_c_planes = 1
    elif isym == 2:
        # C0-C180 symmetry: planes from 0 to 180
        num_c_planes = mc
    elif isym == 3:
        # C90-C270 symmetry: planes from 270 to 90 (wrapping)
        num_c_planes = mc
    elif isym == 4:
        # Quadrant symmetry: planes from 0 to 90
        num_c_planes = mc
    else:
        num_c_planes = mc

    # Parse C-angles (one per line)
    c_angles = []
    for i in range(num_c_planes):
        try:
            c_angles.append(float(lines[idx + i]))
        except (IndexError, ValueError) as e:
            if strict:
                raise LDTDataError(f"Error parsing C-angle at line {idx + i + 1}: {e}") from None
            c_angles.append(0.0)
    idx += num_c_planes
    c_angles = np.array(c_angles)

    # Parse G-angles (one per line)
    g_angles = []
    for i in range(ng):
        try:
            g_angles.append(float(lines[idx + i]))
        except (IndexError, ValueError) as e:
            if strict:
                raise LDTDataError(f"Error parsing G-angle at line {idx + i + 1}: {e}") from None
            g_angles.append(0.0)
    idx += ng
    g_angles = np.array(g_angles)

    # Parse intensity values (one per line, organized by C-plane then G-angle)
    # Total values = num_c_planes * ng
    num_values = num_c_planes * ng
    values = []
    for i in range(num_values):
        try:
            values.append(float(lines[idx + i]))
        except (IndexError, ValueError) as e:
            if strict:
                raise LDTDataError(f"Error parsing intensity at line {idx + i + 1}: {e}") from None
            values.append(0.0)

    # Reshape to (num_c_planes, ng) - values[c_index, g_index]
    values = np.array(values).reshape(num_c_planes, ng)

    return c_angles, g_angles, values


def complete_ldt_symmetry(
    c_angles: np.ndarray,
    g_angles: np.ndarray,
    values: np.ndarray,
    isym: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Complete angle coverage based on LDT symmetry type.

    For storing in Photometry:
    - c_angles map to phis (horizontal/azimuth angles)
    - g_angles map to thetas (vertical angles from nadir)

    Args:
        c_angles: C-plane angles from file
        g_angles: G (gamma) angles from file
        values: Intensity values with shape (len(c_angles), len(g_angles))
        isym: Symmetry type (0-4)

    Returns:
        Tuple of (phis, thetas, expanded_values)
    """
    thetas = g_angles.copy()

    if isym == 0:
        # No symmetry: full 360 coverage already present
        phis = c_angles.copy()
        expanded_values = values.copy()

    elif isym == 1:
        # Axially symmetric: single C-plane, replicate for all angles
        # Return single phi=0 to let Photometry._infer_symmetry detect AXIAL
        phis = np.array([0.0])
        expanded_values = values.copy()  # shape (1, ng)

    elif isym == 2:
        # C0-C180 symmetry: mirror around 180
        # File contains 0 to 180, we store as-is and let Photometry handle HALF symmetry
        phis = c_angles.copy()
        expanded_values = values.copy()

    elif isym == 3:
        # C90-C270 symmetry: angles go from 270 to 90 (wrapping through 0)
        # Need to reorder to standard 0-based convention
        # Transform to 0-180 range for HALF symmetry handling
        phis_raw = c_angles.copy()

        # Convert 270-360 range to -90 to 0, then shift everything to 0-180
        # Example: [270, 280, ..., 350, 0, 10, ..., 90] -> [0, 10, ..., 90, ...]
        # This is tricky - we need to remap to standard coordinates

        # Find where angles wrap (from high to low or cross 0/360 boundary)
        # Simplest approach: subtract 270 and normalize to 0-180
        normalized = (phis_raw - 270) % 360

        # Sort by normalized angle and reorder values
        sort_idx = np.argsort(normalized)
        phis = normalized[sort_idx]
        expanded_values = values[sort_idx]

        # Now we have 0-180 range, which maps to HALF symmetry

    elif isym == 4:
        # Quadrant symmetry: 0-90 coverage
        # Return as-is and let Photometry._infer_symmetry detect QUAD
        phis = c_angles.copy()
        expanded_values = values.copy()

    else:
        # Unknown symmetry, return as-is
        phis = c_angles.copy()
        expanded_values = values.copy()

    return phis, thetas, expanded_values


def convert_ldt_to_candela(
    values: np.ndarray,
    total_flux: float,
) -> np.ndarray:
    """
    Convert cd/klm (candela per kilolumen) to absolute candela.

    LDT files store intensity values normalized to 1000 lumens.
    To get absolute candela: candela = (cd_per_klm * total_flux) / 1000

    Args:
        values: Intensity values in cd/klm
        total_flux: Total luminous flux in lumens

    Returns:
        Absolute candela values
    """
    return (values * total_flux) / 1000.0


def convert_candela_to_ldt(
    values: np.ndarray,
    total_flux: float,
) -> np.ndarray:
    """
    Convert absolute candela to cd/klm for LDT output.

    Args:
        values: Absolute candela values
        total_flux: Total luminous flux in lumens

    Returns:
        Values in cd/klm
    """
    if total_flux <= 0:
        # Avoid division by zero; return normalized to max
        max_val = values.max()
        if max_val > 0:
            return (values / max_val) * 1000.0
        return values.copy()
    return (values * 1000.0) / total_flux


def infer_symmetry_from_photometry(symmetry: "LampSymmetry") -> int:
    """
    Convert LampSymmetry enum to LDT Isym value.

    Args:
        symmetry: LampSymmetry enum value

    Returns:
        LDT Isym integer (0-4)
    """
    from ..photometry import LampSymmetry

    mapping = {
        LampSymmetry.NONE: 0,
        LampSymmetry.AXIAL: 1,
        LampSymmetry.HALF: 2,
        LampSymmetry.QUAD: 4,
        LampSymmetry.UNKNOWN: 0,
    }
    return mapping.get(symmetry, 0)
