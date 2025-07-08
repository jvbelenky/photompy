import pathlib
import importlib.resources as pkg_resources
import photompy.ies as ies 
import pytest

ROOT = pathlib.Path(__file__).parent

@pytest.fixture(scope="session")
def sample_path():
    """Return pathlib.Path to tests/data/ directory."""
    return ROOT / "data"

@pytest.fixture(scope="session")
def load_ies(sample_path):
    """Factory that loads a sample file by name and returns (header, photometry)."""
    def _loader(name: str):
        with open(sample_path / name, "r") as fp:
            return ies.IESFile.read(fp)
    return _loader
