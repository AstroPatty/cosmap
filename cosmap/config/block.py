from pydantic import BaseModel

from cosmap.config.analysis import CosmapParameters


class CosmapParameterException(Exception):
    pass


def create_analysis_block(name, analysis_template, values):
    """
    Create a CosmapParameters object that can be used for a given analysis.
    The top-level fields of the analysis template are used to control high-level
    paramters, like number of threads. Everything else will be found within a sub-block.

    """
    template = CosmapParameters
    # Remove the fields that are top-level
    ref_values = find_ref_values(values)
    if ref_values:
        values = resolve_references(values, ref_values)
    top_fields = {
        n: values[n] for n in CosmapParameters.__fields__ if n in values.keys()
    }
    new_analysis_paramters = {
        n: value for n, value in values.items() if n not in top_fields
    }
    analysis_block = create_parameter_block(
        "analysis_parameters", analysis_template, new_analysis_paramters
    )
    top_fields.update({"analysis_parameters": analysis_block})
    top_block = create_parameter_block("Main", template, top_fields)
    top_block.analysis_parameters = analysis_block
    return top_block


def find_ref_values(values):
    rvalues = {}
    for key, pvalue in values.items():
        if isinstance(pvalue, str) and pvalue.startswith("@"):
            rvalues.update({key: pvalue})
        elif isinstance(pvalue, dict):
            found_values = find_ref_values(pvalue)
            found_values = {f"{key}.{k}": v for k, v in found_values.items()}
            rvalues.update(found_values)
    return rvalues


def resolve_references(values, ref_values):
    for param_key, ref_key in ref_values.items():
        ref_path = ref_key.strip("@").split(".")
        obj = values
        for p in ref_path:
            try:
                obj = obj[p]
            except KeyError:
                obj = {}
                raise CosmapParameterException(
                    f"Value {ref_key} is referenced in config but is not present!"
                )

        param_path = param_key.split(".")
        param_name = param_path[-1]
        param_obj = values
        for p in param_path[:-1]:
            param_obj = param_obj[p]
        param_obj[param_name] = obj

    return values


def create_parameter_block(name: str, template: BaseModel, values: dict):
    block = template(**values, name=name)
    return block
