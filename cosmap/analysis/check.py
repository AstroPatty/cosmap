"""
Routines for checking an analysis
"""

from cosmap.analysis import Analysis


def check_analysis(analysis: Analysis) -> bool:
    """
    Check that the analysis actually runs. This performs the following:

    1. Draw a sample from the sampler
    2. Pass the sampler through the analysis pipeline
    3. Send the results to the parser.

    If any of these steps fails, an exception is raised with details
    of where the failure occured.
    """
    pass
