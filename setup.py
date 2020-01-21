import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="tidal-parser",
    version="0.0.1.post1",
    py_modules=['tidal_parser'],
    author="Daniel Koch",
    author_email="daniel.p.koch@gmail.com",
    description="Python parser for binary log files written with the TiDaL C++ logging library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    url="https://github.com/dpkoch/tidal",
    project_urls={
        "Bug Tracker": "https://github.com/dpkoch/tidal/issues",
        "Documentation": "https://github.com/dpkoch/tidal",
        "Source Code": "https://github.com/dpkoch/tidal",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires = [
        'numpy'
    ],
    python_requires='>=3.6',
)
