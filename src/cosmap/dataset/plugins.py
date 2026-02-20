from dask.distributed.diagnostics.plugin import WorkerPlugin
from heinlein import load_dataset
from pydantic import BaseModel

"""
At present, datasets are attached to Dask workers as plugins. Ideally, a dataset
would operate a server process that would be queried by the workers. In practice though,
some data types cannot be pickled, so we need the worker to have direct access to the 
dataset.

This means we do have spin up one copy of the dataset for each worker. We hope to 
improve this in the future.
"""


class heinleinPlugin(WorkerPlugin):
    def __init__(self, dataset_name):
        self.dataset_name = dataset_name

    def setup(self, worker):
        self.dataset = load_dataset(self.dataset_name)
        worker.dataset = self.dataset

    def teardown(self, worker):
        del worker.dataset


known_wrappers = {"heinlein": heinleinPlugin}


def get_dataset(dataset_parameters: BaseModel):
    return _get_dataset(**dataset_parameters.dict())


def _get_dataset(dataset_wrapper: str, dataset_name: str, *args, **kwargs):
    """
    Get a dataset from a given wrapper. In the future, we will
    support custom wrappers.
    """
    if dataset_wrapper not in known_wrappers:
        raise ValueError(f"Unknown wrapper {dataset_wrapper}")
    wrapper = known_wrappers[dataset_wrapper]
    return wrapper(dataset_name)
