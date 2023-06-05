from cosmap.analyses import analysis_old
from abc import ABC, abstractmethod 
from astropy.coordinates import SkyCoord
from heinlein.region import BaseRegion
from heinlein.dataset import dataset


def get_plugins(plugins: list):
    return {t: triggers[t] for t in plugins}

class DatasetProxy:
    allowed_fs = ["cone_search"]
    requires = ["dataset"]

    def __init__(self, dataset: dataset.Dataset, max_requests = 1):
        self.max_requests = max_requests
        self.dataset = dataset
        self.n = 0

    def __getattr__(self, __key, *args, **kwargs):
        if self.n >= self.max_requests:
            raise analysis_old.CosmapAnalysisError("This dataset proxy object has already used all its allowed requests")
        if __key in self.allowed_fs:
            return getattr(self.dataset, __key)
        else:
            raise AttributeError(f"This dataset proxy does not allow usage of the function {__key}")

triggers = {"request_comparison_data": DatasetProxy}
