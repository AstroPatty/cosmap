from cosmap.config.block import create_analysis_block
from cosmap.analysis.analysis import CosmapAnalysis
from devtools import debug
from pydantic.utils import deep_update

class CosmapConfigException(Exception):
    pass

def build_analysis_object(analysis_data, run_configuration, **kwargs):
    """
    Construct an analysis object, assuming the analysis has been installed
    by `cosmap install`

    Parameters
    ----------
    base_analysis: str
        The name of the analysis
    config: dict
        The configuration for the analysis, usually read from a file

    Returns
    -------
    analysis_object: CosmapAnalysis    
    """
    module = analysis_data["module"]
    transformations = analysis_data["transformations"]
    additional_parameters = analysis_data["parameters"]
    run_configuration.update({"definition_module": module,"transformations": transformations})
    config_definition = getattr(module, "config")
    try:
        main_config_definition = getattr(config_definition, "Main")
    except AttributeError:
        raise CosmapConfigException(f"The analysis config for \'{module.__name__}\' does not have a 'Main' config block")
    run_configuration = deep_update(run_configuration, additional_parameters)
    block = create_analysis_block("Main", main_config_definition, run_configuration)
    block.analysis_parameters.transformations = transformations
    analysis_object = CosmapAnalysis(analysis_paramters=block, **kwargs)
    return analysis_object

