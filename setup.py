from setuptools import setup, find_packages
from pathlib import Path
import re

VERSION_RE = re.compile(r'__version__\s*=\s*"([^"]+)"')

def read_version(path) -> str:
    return VERSION_RE.search(path.read_text()).group(1)

with open("README.md", "r") as fh:
    long_description = fh.read()
    setup(
        name="photompy",
        url="https://github.com/jvbelenky/photompy",
        version=read_version(Path(__file__).parent / 'src' / 'photompy' / '_version.py'),
        author="J. Vivian Belenky",
        author_email="j.vivian.belenky@outlook.com",
        description="A library for reading, writing, and viewing photometric files.",
        long_description=long_description,
        long_description_content_type="text/markdown",
        packages=find_packages('src'),
        package_dir={'': 'src'},
        zip_safe=True,
        python_requires=">=3.8",
        install_requires=[
            "numpy",
            "matplotlib",
        ],        
        classifiers=[
            "Programming Language :: Python :: 3",
            "Operating System :: OS Independent",
            "License :: OSI Approved :: MIT License",
        ],
    )
