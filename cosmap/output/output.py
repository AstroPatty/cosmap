from abc import ABC, abstractmethod
from ast import parse
import logging
from multiprocessing import Lock
from pathlib import Path
from typing import List, Union
import pandas as pd
from . import parser

class outputHandler(ABC):

    def __init__(self, path: Path, parser: parser.cosmapOutputParser, *args, **kwargs):
        self._path = path
        self._parser = parser()
        self._lock = Lock() 

    @abstractmethod
    def write_output(self, *args, **kwargs):
        pass
    
    def set_lock(self, lock):
        self._lock = lock

    def take_output(self, output, *args, **kwargs):
        parsed_output = self._parser(output)
        self._take_output(parsed_output)

    def _take_output(self, output, *args, **kwargs):
        pass


class csvOutputHandler(outputHandler):

    def __init__(self, path: Path, parser: parser.cosmapOutputParser, columns: List[str], *args, **kwargs):
        super().__init__(path, parser, *args, **kwargs)
        self._columns = set(columns)
        self._df = pd.DataFrame(columns=columns)
    
    def __len__(self):
        return len(self._df)

    def write_output(self, *args, **kwargs):
        with self._lock:
            self._df.to_csv(self._path, *args, **kwargs)

    def _take_output(self, output: pd.DataFrame, *args, **kwargs):
        if (o := set(output.columns)) != self._columns:
            print("Error! Output handler was given an output with different columns!")
            print(f"Expected columns {self._columns} but got {o}")
            return
        
        with self._lock:
            self._df = pd.concat([self._df, output], ignore_index=True)

class MultiCsvOutputHandler(outputHandler):

    def __init__(self, paths: dict, parsers: Union[dict, parser.cosmapOutputParser], columns: Union[dict, List[str]], *args, **kwargs):
        super().__init__(paths, parsers, *args, **kwargs)
        output_keys = set(paths.keys())
        path_strings = [str(p) for p in paths]
        if len(set(path_strings)) != len(path_strings):
            raise FileExistsError("The same path was provided for multiple outputs!")

        if type(parsers) == dict:
            missing = output_keys - set(parsers.keys())
            if len(missing) != 0:
                raise KeyError(f"Missing output parsers for {missing}")
        else:
            _parsers = {key: parsers for key in paths.keys()}

        if type(columns) == dict:
            missing = output_keys - set(columns.keys())
            if len(missing) != 0:
                raise KeyError(f"Missing column definitions for {missing}")
        else:
            _columns = {k: columns for k in paths.keys()}

        self._output_handlers = {}
        for key, path in paths.items():
            output_handler = csvOutputHandler(path, _parsers[key], _columns[key])
            self._output_handlers.update({key: output_handler})
    
    def __len__(self):
        return len(self._df)

    def write_output(self, *args, **kwargs):
        for handler in self._output_handlers.values():
            handler.write_output()
    

    def take_output(self, output: dict, *args, **kwargs):
        output_keys = set(output.keys())
        if not output_keys.issubset(self._output_handlers.keys()):
            raise KeyError("Recieved data for an output that doesn't exist!")
        for key, out in output.items():
            self._output_handlers[key].take_output(out)