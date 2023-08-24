class CosmapBadSampleError(Exception):
    """
    Exception raised by the analysis when a sample
    is not valid. This will trigger the sampler to generate
    a new sampler

    Attributes:
        message -- explanation of the error
    """

    pass
