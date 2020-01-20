# TiDaL

TiDaL is a **ti**me-series **da**ta **l**ogging utility for C++ applications. It consists of two parts:

  - A header-only C++ library for logging numerical data (scalars or [Eigen](http://eigen.tuxfamily.org/) vectors/matrices), with an associated timestamp, to a file
  - A Python module for parsing log-file data into numpy arrays for further processing and/or plotting

## Table of Contents

  1. [Log format](#log-format)
  2. [C++ logging](#c-logging)
     1. [Usage](#usage)
        1. [Scalar Stream](#scalar-stream)
        2. [Vector Stream](#vector-stream)
        3. [Matrix Stream](#matrix-stream)
     2. [Including in your project](#including-in-your-project)
  3. [Python parsing](#python-parsing)

## Log format

Each log file can contain multiple named "streams," where each stream is an independent time series. The time stamps need not be synchronized between streams. Each stream can be one of the following types:

  - **Scalar**: More properly, a tuple of any combination of the supported scalar types (signed and unsigned integers, single- or double-precision floating point numbers, or boolean). Labels for each of the fields in the tuple can also be written to the log file.
  - **Vector**: A one-dimensional vector of any of the supported scalar types
  - **Matrix**: A two-dimensional matrix of any of the supported scalar types

Data is stored in a binary format in the log files, with minimal metadata overhead. As a result, logging and parsing are fast and the files are compact.

## C++ logging

Note: Requires C++17 support.

### Usage

Example usage can also be seen in the file `examples/example.cpp`.

Each log file is managed by a `Log` object:

``` cpp
#include <tidal/tidal.h>

tidal::Log log("filename.bin");
```

Streams are added by calling the appropriate `add_<type>_stream()` method on the `Log` object, which then returns a `std::shared_ptr<>` to the `Stream` object that provides a `log()` function for actually writing data to that stream in the log file. Streams can be added at any time, even if data has already been logged to other streams.

Specific instructions for each stream type are given below.

#### Scalar Stream

A scalar stream can contain any number of elements that are of the supported scalar types.
The supported scalar types are `uint8_t`, `int8_t`, `uint16_t`, `int16_t`, `uint32_t`, `int32_t`, `uint64_t`, `int64_t`, `float`, `double`, and `bool`. Equivalent types such as `int` instead of `int32_t` are also supported.

For example, a scalar stream named "My Scalar Stream" and consisting of a `double`, an `int`, and a `bool` would be added and then used as

``` cpp
auto scalar_stream = log.add_scalar_stream<double, int, bool>("My Scalar Stream");

uint64_t timestamp = 1234567;
scalar_stream->log(timestamp, 23.5, 42, true);
```

The SFINAE implementation of the library ensures at compile time that only the correct number and types of values are passed to the `log()` function. The type of `scalar_stream` in this example is `std::shared_ptr<tidal::Log::ScalarStream<double,int,bool>>`.

Additionally, scalar streams support adding labels for each of the fields, such as

``` cpp
scalar_stream->set_labels("x", "y", "z");
```

where the correct number of labels is enforced at compile time.

#### Vector Stream

A vector stream is used to log fixed-size Eigen column vectors, such as `Eigen::Vector3d` or `Eigen::Matrix<double, 6, 1>`. Vector streams are added by calling the `add_vector_stream<>()` method, whose template arguments are the datatype and length of the Eigen vector.

For example, a vector stream named "My Vector Stream" for vectors of type `Eigen::Vector3d` would be added and then used as

``` cpp
#include <eigen3/Eigen/Core>

auto vector_stream = log.add_vector_stream<double, 3>("My Vector Stream");

uint64_t timestamp = 1234567;
Eigen::Vector3d x;
x << 1.0, 2.0, 3.0;

vector_stream->log(timestamp, x);
```

The type of `vector_stream` in this example is `std::shared_ptr<tidal::Log::VectorStream<double,3>>`.

#### Matrix Stream

A matrix stream is used to log fixed-size Eigen matrices, such as `Eigen::Matrix3d` or `Eigen::Matrix<double, 6, 4>`. Matrix streams are added by calling the `add_matrix_stream<>()` method, whose template arguments are the datatype, rows, and columns of the Eigen matrix.

For example, a matrix stream named "My Matrix Stream" for matrices of type `Eigen::Matrix3d` would be added and then used as

``` cpp
#include <eigen3/Eigen/Core>

auto matrix_stream = log.add_matrix_stream<double, 3, 3>("My Matrix Stream");

uint64_t timestamp = 1234567;
Eigen::Matrix3d X = Eigen::Matrix3d::Identity();

matrix_stream->log(timestamp, X);
```

The type of `matrix_stream` in this example is `std::shared_ptr<tidal::Log::MatrixStream<double,3,3>>`.

### Including in your project

The entire logging library is contained in the header file `tidal.h`. The easiest way to include this library in your project is probably to add it as a submodule.

For example, with a CMake-based project using Git, I might add this library in the `lib/tidal` directory with

``` sh
git submodule add https://github.com/dpkoch/tidal.git lib/tidal
```

Then in my `CMakeLists.txt` I may have something like

``` cmake
include(
  # other include directories
  lib/tidal/include
)
```

After which I can include the header file with

``` c++
#include <tidal/tidal.h>
```

## Python parsing

The python parsing package is available from [Python Package Index](https://pypi.org/) as the `tidal-parser` package. This can be installed with pip:

``` sh
python3 -m pip install --user tidal-parser
```

A log file is parsed by creating a `Parser` object with the location of the log file as its argument:

``` python
from tidal_parser import Parser

log = Parser('/path/to/my/log/file.bin')
```

The data is then accessed as numpy arrays through the `time` and `data` members of the `Parser` object. These members are Python dictionaries whose keys are the stream names specified by the C++ `add_<type>_stream()` methods described above.

The following examples show how the streams added in the C++ snippets above might be accessed:

``` python
from tidal_parser import Parser

log = Parser("filename.bin")

# scalar stream
scalar_time = log.time['My Scalar Stream']
x = log.data['My Scalar Stream']['x']
y = log.data['My Scalar Stream']['y']
z = log.data['My Scalar Stream']['z']

# vector stream
vector_time = log.time['My Vector Stream']
vector_data = log.data['My Vector Stream'] # returns nx3 array, where n is the number of timesteps
v_0 = log.data['My Vector Stream'][:,0] # get the 1st element of the vector across all timesteps

# matrix stream
matrix_time = log.time['My Matrix Stream']
matrix_data = log.data['My Matrix Stream'] # returns nx3x3 array, where n is the number of timesteps
m_1_2 = log.data['My Matrix Stream'][:,1,2] # get the (1,2) element of the matrix across all timesteps
```