import json
import toml
from lenskappa.analysis import analysis, kappa_analysis, kappaSet, kappaEnsemble
from pathlib import Path
import sys
import logging

def run_analysis():

    config_path = Path(sys.argv[1])
    if config_path.suffix == ".toml":
        loader = toml.load
    elif config_path.suffix == ".json":
        loader = json.load

    with open(config_path) as f:
        config_data = loader(f)
    
    base_analysis = config_data["base-analysis"]
    if base_analysis == "kappa_set":
        mod = kappaSet
        path = Path(mod.__file__).parents[0] / "kappa_set_template.json"

    elif base_analysis == "kappa_ensemble":
        mod = kappaEnsemble
        path = Path(mod.__file__).parents[0] / "kappa_ensemble_template.json"

    elif base_analysis == "kappa":
        mod = kappa_analysis
        path = Path(mod.__file__).parents[0] / "kappa_template.json"
    
    else:
        raise analysis.InferenceException(f"Expected one of kappa_set, kappa_ensemble, kappa for the base analysis but found {base_analysis}")

    with open(path) as f:
        base_analysis_config = json.load(f)
    
    inf = analysis.build_analysis(config_data, base_analysis_config, mod)
    inf.run_analysis()
