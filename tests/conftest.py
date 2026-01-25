import pathlib
import numpy as np
import photompy.ies as ies
from photompy.photometry import Photometry, PhotometricType, LampSymmetry
import pytest

ROOT = pathlib.Path(__file__).parent


@pytest.fixture(scope="session")
def sample_path():
    """Return pathlib.Path to tests/data/ directory."""
    return ROOT / "data"


@pytest.fixture(scope="session")
def load_ies(sample_path):
    """Factory that loads a sample file by name and returns IESFile."""
    def _loader(name: str):
        with open(sample_path / name, "r") as fp:
            return ies.IESFile.read(fp)
    return _loader


@pytest.fixture
def simple_photometry():
    """Create a simple Photometry for unit testing."""
    thetas = np.array([0, 30, 60, 90])
    phis = np.array([0, 90])
    values = np.array([
        [100, 80, 40, 10],  # phi=0
        [100, 80, 40, 10],  # phi=90
    ])
    return Photometry(
        thetas=thetas,
        phis=phis,
        values=values,
        photometric_type=PhotometricType.C
    )


@pytest.fixture
def axial_photometry():
    """AXIAL symmetry (single phi=0)."""
    thetas = np.array([0, 45, 90])
    phis = np.array([0])
    values = np.array([[100, 70, 20]])
    return Photometry(
        thetas=thetas,
        phis=phis,
        values=values,
        photometric_type=PhotometricType.C
    )


@pytest.fixture
def quad_photometry():
    """QUAD symmetry (0-90 phi range)."""
    thetas = np.array([0, 45, 90])
    phis = np.array([0, 45, 90])
    values = np.array([
        [100, 70, 20],
        [100, 65, 18],
        [100, 60, 15],
    ])
    return Photometry(
        thetas=thetas,
        phis=phis,
        values=values,
        photometric_type=PhotometricType.C
    )


@pytest.fixture
def half_photometry():
    """HALF symmetry (0-180 phi range)."""
    thetas = np.array([0, 45, 90])
    phis = np.array([0, 90, 180])
    values = np.array([
        [100, 70, 20],
        [100, 65, 18],
        [100, 60, 15],
    ])
    return Photometry(
        thetas=thetas,
        phis=phis,
        values=values,
        photometric_type=PhotometricType.C
    )


@pytest.fixture
def full_photometry():
    """NONE symmetry (full 0-360 phi range)."""
    thetas = np.array([0, 90, 180])
    phis = np.array([0, 90, 180, 270, 360])
    values = np.ones((5, 3)) * 100
    return Photometry(
        thetas=thetas,
        phis=phis,
        values=values,
        photometric_type=PhotometricType.C
    )
