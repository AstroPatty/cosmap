from typing import Protocol, runtime_checkable

import astropy.units as u
from astropy.coordinates import SkyCoord

from .plugins import get_dataset

__all__ = ["CosmapDataset", "get_dataset"]


@runtime_checkable
class CosmapDataset(Protocol):
    """
    This simply defines the interface that a dataset must implement
    in order to be used by cosmap. At the time of writing, we are using
    `heinlein` as our dataset interaction library. However, this protocol
    just ensures that users can write their own logic, if they so choose.
    """

    def cone_search(
        self, center: SkyCoord, radius: u.Quantity, dtypes: list, *args, **kwargs
    ) -> dict:
        """
        A basic cone search utility. This should return a dictionary with the keys
        matching the dtype names, and the values being the data.
        """
        pass
