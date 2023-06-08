from cosmap.config.analysis import CosmapAnalysisParamters
from cosmap.config.models import SingleValueModel
from pydantic import BaseModel
import types
import inspect

def create_analysis_block(name, analysis_template, values):

    template = CosmapAnalysisParamters
    exclude = ["analysis_parameters"]
    analysis_parameters = values
    top_fields = {n for n in CosmapAnalysisParamters.__fields__ if n not in exclude}
    new_analysis_paramters = {n: analysis_parameters.pop(n) for n in top_fields if n in values}

    analysis_block = create_parameter_block(name, analysis_template, analysis_parameters)
    new_analysis_paramters.update({"analysis_parameters": analysis_block})


    return create_parameter_block("Main", template, new_analysis_paramters)


def create_parameter_block(name: str, template: CosmapAnalysisParamters, values: dict):
    template_fields = template.__fields__
    parameter_values = {}
    for field_name, field in template_fields.items():
        parameter_value = values.get(field_name, {})
        if type(field.type_) == types.UnionType:
            allowed_types = field.type_.__args__
            if issubclass(allowed_types[0], SingleValueModel):
                cls, parsed_parameter_value = handle_single_value(allowed_types[0], parameter_value)
                parameter_values.update({field_name: parsed_parameter_value})
            elif parameter_value:
                parameter_values.update({field_name:parameter_value})
        elif isinstance(parameter_value, BaseModel):
            parameter_values.update({field_name: parameter_value})

        elif inspect.isclass(field.type_) and issubclass(field.type_, BaseModel):
            block = create_parameter_block(field_name, field.type_, parameter_value)
            parameter_values.update({field_name: block})

        elif parameter_value:
            parameter_values.update({field_name: parameter_value})
    block = template(**parameter_values)
    return block


def handle_single_value(class_: BaseModel, input_values: dict):
    param = class_(**input_values)
    return param.get_value_type(), param.get_value()

def build_paramter_block_class(name: str, block_data: dict) -> dict:
    class Config:
        arbitrary_types_allowed = True
    
    class_input = block_data
    class_input.update({"Config": Config})
    block_class = type(name, (BaseModel,), class_input)
    return block_class
