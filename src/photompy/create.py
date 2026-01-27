"""
Convenience functions for creating IES and LDT files from angular distribution arrays.

These functions provide a streamlined API for generating photometric files
from raw numpy arrays, enforcing standard-required metadata fields.
"""

import numpy as np
from .photometry import Photometry, PhotometricType
from .ies import IESFile
from .ldt import LDTFile


def create_ies(
    thetas: np.ndarray,
    phis: np.ndarray,
    values: np.ndarray,
    *,
    # Required by IES LM-63 spec (no defaults)
    manufacturer: str,
    lumcat: str,
    test: str,
    testlab: str,
    issuedate: str,
    # Optional parameters
    photometric_type: PhotometricType = PhotometricType.C,
    **kwargs,
) -> IESFile:
    """
    Create an IESFile directly from angular distribution arrays.

    This is a convenience function that combines Photometry creation
    with IESFile.from_photometry() in a single call.

    Per IES LM-63-2002/2019, the following keywords are REQUIRED and must
    be provided by the caller (no defaults):
    - manufacturer: Manufacturer name (MANUFAC keyword)
    - lumcat: Luminaire catalog number (LUMCAT keyword)
    - test: Test report number/description (TEST keyword)
    - testlab: Testing laboratory name (TESTLAB keyword)
    - issuedate: Test completion date, format YYYY-MM-DD (ISSUEDATE keyword)

    Args:
        thetas: Vertical angles in degrees (0-180 for Type C, -90 to 90 for Type A/B)
        phis: Horizontal angles in degrees
        values: 2D array of candela values, shape (len(phis), len(thetas))
        manufacturer: Manufacturer name (required)
        lumcat: Luminaire catalog number (required)
        test: Test report number/description (required)
        testlab: Testing laboratory name (required)
        issuedate: Test completion date (required)
        photometric_type: Type C, B, or A (default C)
        **kwargs: Additional arguments passed to IESFile.from_photometry()
            (luminaire, lumens_per_lamp, input_watts, num_lamps, width, length,
            height, units, ballast_factor, tilt, version, file_generation, keywords)

    Returns:
        IESFile ready for writing

    Raises:
        TypeError: If any required parameter is missing

    Example:
        >>> from photompy import create_ies
        >>> import numpy as np
        >>>
        >>> thetas = np.linspace(0, 90, 19)
        >>> phis = np.array([0])
        >>> values = np.cos(np.deg2rad(thetas))[None, :] * 1000
        >>>
        >>> ies = create_ies(
        ...     thetas, phis, values,
        ...     manufacturer="Acme Lighting",
        ...     lumcat="DL-100",
        ...     test="Performance Test 2026-001",
        ...     testlab="Acme Test Lab",
        ...     issuedate="2026-01-27",
        ...     input_watts=15,
        ... )
        >>> ies.write("downlight.ies")
    """
    phot = Photometry(thetas, phis, values, photometric_type)
    return IESFile.from_photometry(
        phot,
        manufacturer=manufacturer,
        lumcat=lumcat,
        test=test,
        testlab=testlab,
        issuedate=issuedate,
        **kwargs,
    )


def create_ldt(
    thetas: np.ndarray,
    phis: np.ndarray,
    values: np.ndarray,
    *,
    # Required parameters (no defaults)
    manufacturer: str,
    luminaire_name: str,
    # Optional parameters
    photometric_type: PhotometricType = PhotometricType.C,
    **kwargs,
) -> LDTFile:
    """
    Create an LDTFile directly from angular distribution arrays.

    This is a convenience function that combines Photometry creation
    with LDTFile.from_photometry() in a single call.

    The EULUMDAT format requires certain fields. The following are required
    by this function (no defaults):
    - manufacturer: Company/manufacturer name (line 1)
    - luminaire_name: Luminaire description (line 9)

    Args:
        thetas: Vertical angles in degrees (0-180 for Type C)
        phis: Horizontal angles in degrees
        values: 2D array of candela values, shape (len(phis), len(thetas))
        manufacturer: Company/manufacturer name (required)
        luminaire_name: Luminaire description (required)
        photometric_type: Type C, B, or A (default C)
        **kwargs: Additional arguments passed to LDTFile.from_photometry()
            (luminaire_number, luminaire_type, report_number, date_user,
            length, width, height, luminous_length, luminous_width,
            luminous_height, dff, lorl, tilt, num_lamps, lamp_type, total_flux)

    Returns:
        LDTFile ready for writing

    Raises:
        TypeError: If any required parameter is missing

    Example:
        >>> from photompy import create_ldt
        >>> import numpy as np
        >>>
        >>> thetas = np.linspace(0, 90, 19)
        >>> phis = np.array([0])
        >>> values = np.cos(np.deg2rad(thetas))[None, :] * 1000
        >>>
        >>> ldt = create_ldt(
        ...     thetas, phis, values,
        ...     manufacturer="Acme Lighting",
        ...     luminaire_name="Downlight DL-100",
        ...     luminous_width=50,
        ...     luminous_length=50,
        ... )
        >>> ldt.write("downlight.ldt")
    """
    phot = Photometry(thetas, phis, values, photometric_type)
    return LDTFile.from_photometry(
        phot,
        manufacturer=manufacturer,
        luminaire_name=luminaire_name,
        **kwargs,
    )
