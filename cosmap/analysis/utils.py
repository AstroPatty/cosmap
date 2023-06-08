from cosmap.config.models import model
from cosmap.config.block import create_analysis_block
from cosmap.analysis.analysis import CosmapAnalysis
from typing import List
import sys


def build_analysis_object(base_analysis: str, config: dict, **kwargs):
    module = model.get_definition_module(base_analysis)
    transformations = model.get_transformations(base_analysis)
    config.update({"definition_module": module["module"], "definition_path": module["path"]})
    model_block = model.get_model(base_analysis)
    block = create_analysis_block("Main", model_block, config)
    block.analysis_parameters.transformations = transformations
    analysis_object = CosmapAnalysis(analysis_paramters=block, **kwargs)
    return analysis_object

