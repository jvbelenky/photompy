from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()
    setup(
        name="photompy",
        url="https://github.com/jvbelenky/photompy",
        version="0.0.3",
        author="J. Vivian Belenky",
        author_email="j.vivian.belenky@outlook.com",
        description="Utility package for handling photometric files",
        long_description=long_description,
        long_description_content_type="text/markdown",
        classifiers=[
            "Programming Language :: Python :: 3",
            "Operating System :: OS Independent",
            "License :: OSI Approved :: MIT License",
        ],
        packages=find_packages('src'),
        package_dir={'': 'src'},
        zip_safe=True,
        python_requires=">=3.8",
        install_requires=[
            "numpy",
            "matplotlib",
        ],
    )
