import setuptools

setuptools.setup(
    name="tidal-parser",
    version="0.0.1",
    author="Daniel Koch",
    author_email="daniel.p.koch@gmail.com",
    description="Python parser for binary log files written with the TiDaL C++ logging library",
    url="https://github.com/dpkoch/tidal",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
