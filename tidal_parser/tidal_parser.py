# MIT License
#
# Copyright (c) 2020 Daniel Koch
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import io
import struct

import numpy as np


class ParserError(Exception):
    """Base class for parser module exceptions"""
    pass


class InvalidLogFile(ParserError):
    """Indicates the log file format was not valid"""
    pass


class Parser:
    # miscellaneous constants
    EOF = b''
    NULL_TERMINATOR = b'\x00'

    # binary format specification
    MARKER_METADATA = b'\xA5'
    MARKER_LABELS = b'\x66'
    MARKER_DATA = b'\xDB'

    TIMESTAMP_DTYPE = np.dtype('uint64')

    TYPE_STREAM_ID = 'I'  # uint32 (format specifier struct package)
    TYPE_DATA_CLASS = 'B'  # uint8 (format specifier for struct package)
    TYPE_SCALAR_TYPE = 'B'  # uint8 (format specifier for struct package)
    TYPE_DATA_SIZE = 'I'  # uint32 (format specifier for struct package)

    # data class identifiers
    DATACLASS_SCALAR = 0
    DATACLASS_VECTOR = 1
    DATACLASS_MATRIX = 2

    # scalar type identifiers
    SCALAR_TYPES = {0:  'uint8',  # type id: dtype string (numpy)
                    1:  'int8',
                    2:  'uint16',
                    3:  'int16',
                    4:  'uint32',
                    5:  'int32',
                    6:  'uint64',
                    7:  'int64',
                    8:  'float32',
                    9:  'float64',
                    10: 'bool'}

    def __init__(self, filename):
        self.filename = filename

        self.time = {}  # contains timestamps for the data
        self.data = {}  # contains the logged data

        self.metadata = {}  # contains information about the streams
        self.time_bytestream = {}  # bytestream buckets for timestamps
        self.data_bytestream = {}  # bytestream buckets for data

        # binary format decoders
        self.read_stream_id = lambda f: struct.unpack(
            self.TYPE_STREAM_ID, f.read(struct.calcsize(self.TYPE_STREAM_ID)))[0]
        self.read_data_class = lambda f: struct.unpack(
            self.TYPE_DATA_CLASS, f.read(struct.calcsize(self.TYPE_DATA_CLASS)))[0]
        self.read_scalar_type = lambda f: struct.unpack(
            self.TYPE_SCALAR_TYPE, f.read(struct.calcsize(self.TYPE_SCALAR_TYPE)))[0]
        self.read_data_size = lambda f: struct.unpack(
            self.TYPE_DATA_SIZE, f.read(struct.calcsize(self.TYPE_DATA_SIZE)))[0]

        self.format_handler = {self.DATACLASS_SCALAR: self.read_scalar_format,  # data class id: metadata handler function
                               self.DATACLASS_VECTOR: self.read_vector_format,
                               self.DATACLASS_MATRIX: self.read_matrix_format}

        # parse the log file on construction
        self.parse()

        # convert parsed data into numpy arrays
        self.convert()

    def parse(self):
        with open(self.filename, 'rb') as f:
            while True:
                try:
                    byte = f.read(1)
                    if byte == self.MARKER_DATA:
                        self.read_data(f)
                    elif byte == self.MARKER_METADATA:
                        self.read_metadata(f)
                    elif byte == self.MARKER_LABELS:
                        self.read_labels(f)
                    elif byte == self.EOF:
                        break
                    else:
                        raise InvalidLogFile()

                except EOFError:
                    break

    def read_metadata(self, f):

        # get stream ID
        stream_id = self.read_stream_id(f)
        self.metadata[stream_id] = {}

        # get stream name
        self.metadata[stream_id]['name'] = self.read_string(f)

        # get data class
        self.metadata[stream_id]['class'] = self.read_data_class(f)

        # get format dtype
        self.metadata[stream_id]['dtype'] = \
            self.format_handler[self.metadata[stream_id]['class']](f)

        # initialize bytestreams
        self.time_bytestream[stream_id] = io.BytesIO()
        self.data_bytestream[stream_id] = io.BytesIO()

    def read_labels(self, f):
        stream_id = self.read_stream_id(f)

        labels = [self.read_string(f)
                  for _ in range(len(self.metadata[stream_id]['dtype']))]

        self.metadata[stream_id]['labels'] = tuple(labels)
        self.metadata[stream_id]['dtype'].names = self.metadata[stream_id]['labels']

    def read_string(self, f):
        b = io.BytesIO()
        while True:
            byte = f.read(1)
            if byte == b'\x00':
                break
            # TODO check for EOF?
            b.write(byte)
        return b.getvalue().decode()

    def read_scalar_format(self, f):
        num_scalars = self.read_data_size(f)
        dtypes = [self.SCALAR_TYPES[self.read_scalar_type(f)]
                  for _ in range(num_scalars)]

        return np.dtype(','.join(dtypes))

    def read_vector_format(self, f):
        scalar_type = self.read_scalar_type(f)
        elements = self.read_data_size(f)

        return np.dtype('({},){}'.format(
            elements, self.SCALAR_TYPES[scalar_type]))

    def read_matrix_format(self, f):
        scalar_type = self.read_scalar_type(f)
        rows = self.read_data_size(f)
        cols = self.read_data_size(f)

        return np.dtype('({},{}){}'.format(
            rows, cols, self.SCALAR_TYPES[scalar_type]))

    def read_data(self, f):
        stream_id = self.read_stream_id(f)
        self.time_bytestream[stream_id].write(
            f.read(self.TIMESTAMP_DTYPE.itemsize))
        self.data_bytestream[stream_id].write(
            f.read(self.metadata[stream_id]['dtype'].itemsize))

    def convert(self):
        for stream_id in self.metadata.keys():
            self.time[self.metadata[stream_id]['name']] = np.frombuffer(
                self.time_bytestream[stream_id].getvalue(), self.TIMESTAMP_DTYPE)

            dtype = self.metadata[stream_id]['dtype']
            if dtype.ndim == 2:  # transpose matrices after reading from column-major to row-major
                self.data[self.metadata[stream_id]['name']] = np.swapaxes(np.frombuffer(
                    self.data_bytestream[stream_id].getvalue(), dtype), 1, 2)
            else:
                self.data[self.metadata[stream_id]['name']] = np.frombuffer(
                    self.data_bytestream[stream_id].getvalue(), dtype)
