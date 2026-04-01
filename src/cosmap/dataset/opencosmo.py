from pathlib import Path
from typing import Optional

import astropy.units as u
import opencosmo as oc
from astropy.coordinates import SkyCoord
from dask.distributed.diagnostics.plugin import WorkerPlugin


class opencosmoPlugin(WorkerPlugin):
    def __init__(
        self,
        name: Optional[str],
        path: Path,
        dataset_columns: Optional[list[str]],
        **kwargs,
    ):
        self.__files = identify_opencosmo_files(path)
        self.__columns = dataset_columns

    def setup(self, worker):
        dataset = oc.open(self.__files)
        if self.__columns is not None:
            dataset = dataset.select(self.__columns)
        worker.dataset = OpenCosmoProxy(dataset)

    def teardown(self, worker):
        try:
            del worker.dataset
        except AttributeError:
            return


class OpenCosmoProxy:
    def __init__(self, dataset):
        self.__dataset = dataset

    def get_data_from_samples(
        self, coordinates: SkyCoord, dtypes, sample_type, sample_dimensions: u.Quantity
    ):
        assert sample_type == "cone"
        min_ra = coordinates.ra.min()
        max_ra = coordinates.ra.max()
        min_dec = coordinates.dec.min()
        max_dec = coordinates.dec.max()
        # this is just for caching optimization. Does not have to be perfect
        min_ra = min_ra - 2 * sample_dimensions
        max_ra = max_ra - 2 * sample_dimensions
        min_dec = min_dec - 2 * sample_dimensions
        max_dec = max_dec + 2 * sample_dimensions

        for coordinate in coordinates:
            region = oc.make_cone(coordinate, sample_dimensions)
            yield region, {"catalog": self.__dataset.bound(region).get_data()}


def identify_opencosmo_files(path: Path):
    if path.exists() and path.is_file() and path.suffix == ".hdf5":
        return [path]

    elif path.exists() and path.is_dir():
        return list(path.glob("*.hdf5"))

    else:
        raise FileNotFoundError(f"Unable to identify opencosmo files at path {path}")
