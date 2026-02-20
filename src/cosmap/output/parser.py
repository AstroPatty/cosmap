from abc import ABC, abstractmethod

import numpy as np
import pandas as pd


class cosmapParserException(Exception):
    pass


class cosmapOutputParser(ABC):
    output_format = None
    """
    An output parser handles turning raw python data into a structured datatype that can
    be written to a file, database, or other output. For example, a csv parser takes a 
    dictionary of key-value pairs, and turns it into a pandas DataFrame. A parser is 
    combined with an output writer, which actually handles writing the data to disk.

    The parser should keep a working copy of any output it has recieved, unless it is 
    explicitly cleared. This data may or may not be in the same same format as the 
    output that is written to disk, as long as the "get" function returns an object of 
    the type specified by the output_format class variable.
    """

    def __init__(self, *args, **kwargs):
        pass

    @abstractmethod
    def append(self, output, *args, **kwargs):
        pass

    @abstractmethod
    def get(self, *args, **kwargs):
        """
        Get the output from the parser in its current state.
        """
        pass

    @abstractmethod
    def clear(self, *args, **kwargs):
        """
        Clear any previously parsed output.
        """


class dataFrameOutputParser(cosmapOutputParser):
    """
    This parser takes a dictionary of key-value pairs that correspond to a single row in
    a DataFrame, and appends it to a DataFrame. In general, appending is a very
    expensive operation, so this parser allocates memory in chunks, and only increases
    the amount of memory when the chunk fills.

    For large jobs with a large number of outputs, this parser can use a lot of memory.
    To avoid this, this particular parser only stores the current chunk, and appends it
    to the file when it writes. It does check to ensure columns are consistent between
    chunks.
    """

    output_format = pd.DataFrame

    def __init__(self, chunksize=5000, *args, **kwargs):
        self.tally = 0
        self.size = 0
        self.chunksize = chunksize
        self.initialized = False
        self.series = {}

    def initialize(self, columns: list, dtypes: list):
        if dtypes is not None:
            self.dtypes = {c: dtypes[i] for i, c in enumerate(columns)}
            self.columns = set(columns)
            self.series = {
                c: np.empty(self.chunksize, dtype=self.dtypes[c]) for c in columns
            }
            self.initialized = True
            self.size += self.chunksize

    def append(self, data: dict):
        if not self.initialized:
            columns = list(data.keys())
            dtypes = [type(v) for v in data.values()]
            self.initialize(columns, dtypes)
        elif self.tally == self.size:
            self.extend()
        for column, value in data.items():
            if column not in self.columns:
                raise cosmapParserException(
                    f"Parsed data contains column {column}, which is not in the list"
                    "of columns!"
                )
            self.series[column][self.tally] = value
        self.tally += 1

    def extend(self):
        self.size += self.chunksize
        for c in self.series:
            self.series[c] = np.append(
                self.series[c], np.empty(self.chunksize, dtype=self.dtypes[c])
            )

    def get(self, *args, **kwargs):
        if self.tally:
            input_series = {c: self.series[c][: self.tally] for c in self.series}
            result = pd.DataFrame.from_dict(input_series, orient="columns")
            self.clear()
            return result
        # Now, we reset the parser but keep the orig
        return None

    def clear(self, *args, **kwargs):
        """
        Clears any output that has been parsed, but keeps the original configuration.
        """
        self.tally = 0
        self.series = {
            c: np.empty(self.chunksize, dtype=self.dtypes[c])
            for c in self.series.keys()
        }
        self.size = self.chunksize
