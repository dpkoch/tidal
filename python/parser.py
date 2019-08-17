import io
import struct

import numpy as np


class ParserError(Exception):
    """Base class for parser module exceptions"""
    pass


class InvalidLogFile(ParserError):
    """Indicates the log file format was not valid"""
    pass


class Log:
    def __init__(self, filename):
        self.filename = filename

        self.time = {}  # contains timestamps for the data
        self.data = {}  # contains the logged data

        self.metadata = {}  # contains information about the streams
        self.time_bytestream = {}  # bytestream buckets for timestamps
        self.data_bytestream = {}  # bytestream buckets for data

        # binary format specification
        self.EOF = b''
        self.METADATA_MARKER = b'\xA5'
        self.DATA_MARKER = b'\xDB'
        self.LABEL_MARKER = b'\x66'
        self.NULL_TERMINATOR = b'\x00'

        self.TIMESTAMP_DTYPE = np.dtype('u8')

        self.read_stream_id = lambda f: struct.unpack('I', f.read(4))[0]
        self.read_data_class = lambda f: struct.unpack('B', f.read(1))[0]
        self.read_scalar_type = lambda f: struct.unpack('B', f.read(1))[0]
        self.read_data_size = lambda f: struct.unpack('I', f.read(4))[0]

        self.format_handler = {0: self.read_scalar_format,  # data class id: metadata handler function
                               1: self.read_vector_format,
                               2: self.read_matrix_format}
        self.scalar_types = {0: 'u1',  # type id: dtype string
                             1: 'i1',
                             2: 'u2',
                             3: 'i2',
                             4: 'u4',
                             5: 'i4',
                             6: 'u8',
                             7: 'i8',
                             8: 'f4',
                             9: 'f8',
                             10: 'bool'}

        # parse the log file on construction
        self.parse()

        # convert parsed data into numpy arrays
        self.convert()

    def parse(self):
        with open(self.filename, 'rb') as f:
            while True:
                try:
                    byte = f.read(1)
                    if byte == self.DATA_MARKER:
                        self.read_data(f)
                    elif byte == self.METADATA_MARKER:
                        self.read_metadata(f)
                    elif byte == self.LABEL_MARKER:
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

        labels = []
        for _ in range(len(self.metadata[stream_id]['dtype'])):
            labels.append(self.read_string(f))

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
        dtypes = [self.scalar_types[self.read_scalar_type(f)]
                  for _ in range(num_scalars)]

        return np.dtype(','.join(dtypes))

    def read_vector_format(self, f):
        scalar_type = self.read_scalar_type(f)
        elements = self.read_data_size(f)

        return np.dtype('({},){}'.format(
            elements, self.scalar_types[scalar_type]))

    def read_matrix_format(self, f):
        scalar_type = self.read_scalar_type(f)
        rows = self.read_data_size(f)
        cols = self.read_data_size(f)

        return np.dtype('({},{}){}'.format(
            rows, cols, self.scalar_types[scalar_type]))

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


if __name__ == '__main__':
    meh = Log('build/meh.bin')
