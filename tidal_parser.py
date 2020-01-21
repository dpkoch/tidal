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
        self._filename = filename

        self.time = {}  # contains timestamps for the data
        self.data = {}  # contains the logged data

        self._metadata = {}  # contains information about the streams
        self._time_bytestream = {}  # bytestream buckets for timestamps
        self._data_bytestream = {}  # bytestream buckets for data

        # binary format decoders
        self._read_stream_id = lambda f: struct.unpack(
            self.TYPE_STREAM_ID, f.read(struct.calcsize(self.TYPE_STREAM_ID)))[0]
        self._read_data_class = lambda f: struct.unpack(
            self.TYPE_DATA_CLASS, f.read(struct.calcsize(self.TYPE_DATA_CLASS)))[0]
        self._read_scalar_type = lambda f: struct.unpack(
            self.TYPE_SCALAR_TYPE, f.read(struct.calcsize(self.TYPE_SCALAR_TYPE)))[0]
        self._read_data_size = lambda f: struct.unpack(
            self.TYPE_DATA_SIZE, f.read(struct.calcsize(self.TYPE_DATA_SIZE)))[0]

        self._format_handler = {self.DATACLASS_SCALAR: self._read_scalar_format,  # data class id: metadata handler function
                               self.DATACLASS_VECTOR: self._read_vector_format,
                               self.DATACLASS_MATRIX: self._read_matrix_format}

        # parse the log file on construction
        self._parse()

        # convert parsed data into numpy arrays
        self._convert()

    def _parse(self):
        with open(self._filename, 'rb') as f:
            while True:
                try:
                    byte = f.read(1)
                    if byte == self.MARKER_DATA:
                        self._read_data(f)
                    elif byte == self.MARKER_METADATA:
                        self._read_metadata(f)
                    elif byte == self.MARKER_LABELS:
                        self._read_labels(f)
                    elif byte == self.EOF:
                        break
                    else:
                        raise InvalidLogFile()

                except EOFError:
                    break

    def _read_metadata(self, f):

        # get stream ID
        stream_id = self._read_stream_id(f)
        self._metadata[stream_id] = {}

        # get stream name
        self._metadata[stream_id]['name'] = self._read_string(f)

        # get data class
        self._metadata[stream_id]['class'] = self._read_data_class(f)

        # get format dtype
        self._metadata[stream_id]['dtype'] = \
            self._format_handler[self._metadata[stream_id]['class']](f)

        # initialize bytestreams
        self._time_bytestream[stream_id] = io.BytesIO()
        self._data_bytestream[stream_id] = io.BytesIO()

    def _read_labels(self, f):
        stream_id = self._read_stream_id(f)

        labels = [self._read_string(f)
                  for _ in range(len(self._metadata[stream_id]['dtype']))]

        self._metadata[stream_id]['labels'] = tuple(labels)
        self._metadata[stream_id]['dtype'].names = self._metadata[stream_id]['labels']

    def _read_string(self, f):
        b = io.BytesIO()
        while True:
            byte = f.read(1)
            if byte == b'\x00':
                break
            # TODO check for EOF?
            b.write(byte)
        return b.getvalue().decode()

    def _read_scalar_format(self, f):
        num_scalars = self._read_data_size(f)
        dtypes = [self.SCALAR_TYPES[self._read_scalar_type(f)]
                  for _ in range(num_scalars)]

        return np.dtype(','.join(dtypes))

    def _read_vector_format(self, f):
        scalar_type = self._read_scalar_type(f)
        elements = self._read_data_size(f)

        return np.dtype('({},){}'.format(
            elements, self.SCALAR_TYPES[scalar_type]))

    def _read_matrix_format(self, f):
        scalar_type = self._read_scalar_type(f)
        rows = self._read_data_size(f)
        cols = self._read_data_size(f)

        return np.dtype('({},{}){}'.format(
            rows, cols, self.SCALAR_TYPES[scalar_type]))

    def _read_data(self, f):
        stream_id = self._read_stream_id(f)
        self._time_bytestream[stream_id].write(
            f.read(self.TIMESTAMP_DTYPE.itemsize))
        self._data_bytestream[stream_id].write(
            f.read(self._metadata[stream_id]['dtype'].itemsize))

    def _convert(self):
        for stream_id in self._metadata.keys():
            self.time[self._metadata[stream_id]['name']] = np.frombuffer(
                self._time_bytestream[stream_id].getvalue(), self.TIMESTAMP_DTYPE)

            dtype = self._metadata[stream_id]['dtype']
            if dtype.ndim == 2:  # transpose matrices after reading from column-major to row-major
                self.data[self._metadata[stream_id]['name']] = np.swapaxes(np.frombuffer(
                    self._data_bytestream[stream_id].getvalue(), dtype), 1, 2)
            else:
                self.data[self._metadata[stream_id]['name']] = np.frombuffer(
                    self._data_bytestream[stream_id].getvalue(), dtype)
