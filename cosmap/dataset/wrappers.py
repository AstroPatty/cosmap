import heinlein
from pydantic import BaseModel

known_wrappers = {
    "heinlein": heinlein.load_dataset
}

def get_dataset(dataset_parameters: BaseModel):
    return _get_dataset(**dataset_parameters.dict())

def _get_dataset(dataset_wrapper: str, dataset_name: str):
    """
    Get a dataset from a given wrapper. In the future, we will
    support custom wrappers.
    """
    if dataset_wrapper not in known_wrappers:
        raise ValueError(f"Unknown wrapper {dataset_wrapper}")
    wrapper = known_wrappers[dataset_wrapper]
    return wrapper(dataset_name)