from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()
    setup(
        name="ies_utils",
        url="https://github.com/jvbelenky/ies_utils",
        version="0.0.1",
        author="J. Vivian Belenky",
        author_email="j.vivian.belenky@outlook.com",
        description="Utility package for handling .ies (Illuminating Engineering Society) files",
        long_description=long_description,
        long_description_content_type="text/markdown",
        classifiers=[
            "Programming Language :: Python :: 3",
            "Operating System :: OS Independent",
            "License :: OSI Approved :: MIT License",
        ],
        zip_safe=True,
        python_requires=">=3.8",
        install_requires=[
            "numpy",
            "matplotlib",
        ],
        packages=find_packages(),
    )
