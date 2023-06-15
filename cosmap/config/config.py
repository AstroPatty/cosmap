
from cosmap.config import model


class CosmapConfigException(Exception):
    pass

def get_config(input_data: dict):
    config_data = input_data
    base_analysis = config_data.pop("base-analysis", {})
    if not base_analysis:
        raise CosmapConfigException(f"Analysis configuration must include a 'base-analysis' entery!")
    analysis_model = model.get_model(base_analysis)

