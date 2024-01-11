from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd


class cosmapOutputException(Exception):
    pass


class cosmapOutputWriter(ABC):
    """
    This is the base class for all output writers. It handles actually writing
    output to a file. It is combined with a parser, which handles converting
    raw python data into a structured datatype that can be written to a file.
    """

    @abstractmethod
    def write_output(self, output, *args, **kwargs):
        pass


class dataframeCsvWriter(cosmapOutputWriter):
    def __init__(self, path: Path, *args, **kwargs):
        self._path = path

    def write_output(self, output: pd.DataFrame, *args, **kwargs):
        output.to_csv(
            self._path,
            index=False,
            mode="a",
            header=not self._path.exists(),
            *args,
            **kwargs,
        )


known_writers = {"csv": dataframeCsvWriter}


def get_writer(writer_type: str):
    try:
        return known_writers[writer_type]
    except KeyError:
        raise cosmapOutputException(f"Unknown writer type '{writer_type}'")
