from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from loguru import logger
from pydantic import BaseModel

from . import parser, writer


def get_output_handler(output_paramters: BaseModel):
    writer_ = writer.get_writer(output_paramters.write_format)
    if output_paramters.output_formats == "dataframe":
        if output_paramters.output_paths is None:
            return dataframeOutputHandler(output_paramters.base_output_path, writer_)
        else:
            return multiDataframeOutputHandler(output_paramters.output_paths, writer_)


class outputHandler(ABC):
    def write_output(self, *args, **kwargs):
        output = self._parser.get()
        if output is not None:
            self._writer.write_output(output, *args, **kwargs)

    @abstractmethod
    def take_output(self, output, *args, **kwargs):
        pass

    @abstractmethod
    def take_outputs(self, outputs: List[dict], *args, **kwargs):
        pass


class dataframeOutputHandler(outputHandler):
    def __init__(self, path: Path, writer: type, writer_config: dict = {}):
        if path.exists():
            logger.warning(f"Output path {path} already exists, overwriting")
            path.unlink()
        elif not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        self._writer = writer(path=path, **writer_config)
        self._parser = parser.dataFrameOutputParser()

    def take_output(self, output: dict, *args, **kwargs):
        self._parser.append(output)

    def take_outputs(self, outputs: List[dict], *args, **kwargs):
        for output in outputs:
            self.take_output(output, *args, **kwargs)


class multiDataframeOutputHandler(outputHandler):
    def __init__(self, paths: dict, writer: type, writer_config: dict = {}):
        self._handlers = {
            k: dataframeOutputHandler(
                path=v, writer=writer, writer_config=writer_config
            )
            for k, v in paths.items()
        }

    def take_output(self, output: dict, *args, **kwargs):
        """
        Expect a dictionary of dictionaries...
        """
        for k, row in output.items():
            self._handlers[k].take_output(row)

    def take_outputs(self, outputs: List[dict], *args, **kwargs):
        for output in outputs:
            self.take_output(output, *args, **kwargs)

    def write_output(self, *args, **kwargs):
        for handler in self._handlers.values():
            handler.write_output(*args, **kwargs)
