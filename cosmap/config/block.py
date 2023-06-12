from cosmap.config.analysis import CosmapParameters
from cosmap.config.models import SingleValueModel
from pydantic import BaseModel, create_model
import types
import inspect
from copy import copy
from devtools import debug

def create_analysis_block(name, analysis_template, values):
    """
    Create a CosmapParameters object that can be used for a given analysis.
    The top-level fields of the analysis template are used to control high-level
    paramters, like number of threads. Everything else will be found within a sub-block.
    
    """
    template = CosmapParameters
    #Remove the fields that are top-level
    top_fields = {n: values[n] for n in CosmapParameters.__fields__ if n in values.keys()}
    new_analysis_paramters = {n: value for n, value in values.items() if n not in top_fields}
    analysis_block = create_parameter_block("analysis_parameters", analysis_template, new_analysis_paramters)
    top_block = create_parameter_block("Main", template, top_fields)
    top_block.analysis_parameters = analysis_block
    return top_block

def _contains_single_value_model(field):
    if type(field.type_) == types.UnionType:
        allowed_types = field.type_.__args__
        for t in allowed_types:
            try:
                if issubclass(t, SingleValueModel):
                    return True
            except TypeError:
                continue
    elif issubclass(field.type_, SingleValueModel):
        return True
    return False

def create_parameter_block(name: str, template: BaseModel, values: dict, sub_block = False):
    template_fields = template.__fields__
    parameter_values = {}
    new_model_input = {}
    new_model_validators = {}
    for field_name, field in template_fields.items():
        if _contains_single_value_model(field):
            #This field contains one of Cosmap's special models
            if type(field.type_) == types.UnionType:
                print(field.type_)
                raise NotImplementedError(f"{field_name}")
            else:
                cls, parsed_parameter_value = handle_single_value(field.type_, values.get(field_name, {}))
                parameter_values.update({field_name: parsed_parameter_value})
                new_model_input.update({field_name: (cls, ...)})
                #The validators here are responsible for creating the value
                #So we don't actually want them in the new model.
        

        elif inspect.isclass(field.type_) and issubclass(field.type_, BaseModel):
            #This field is a sub-block   
            template_, values_ = create_parameter_block(field_name, field.type_, values.get(field_name, {}), sub_block = True)
            parameter_values.update({field_name: values_})
            new_model_input.update({field_name: (template_, ...)})

        else:
            #This is just a regular Pydantic field
            if field_name in values:
                parameter_values.update({field_name: values[field_name]})
            new_model_input.update({field_name: (field.type_, field.default)})
            new_model_validators.update({field_name: field.validators})

    new_template = create_model(name, **new_model_input, __validators__=new_model_validators, __config__=template.Config)
    if sub_block:
        return new_template, parameter_values
    block = new_template(**parameter_values)
    return block


def _create_parameter_block(name: str, template: BaseModel, values: dict):
    template_fields = template.__fields__
    parameter_values = {}
    new_model_input = {}
    for field_name, field in template_fields.items():
        parameter_value = values.get(field_name, {})
        if type(field.type_) == types.UnionType:
            allowed_types = field.type_.__args__
            if issubclass(allowed_types[0], SingleValueModel):
                cls, parsed_parameter_value = handle_single_value(allowed_types[0], parameter_value)
                parameter_values.update({field_name: parsed_parameter_value})
            elif parameter_value:
                parameter_values.update({field_name:parameter_value})

        if issubclass(field.type_, SingleValueModel):
            cls, parsed_parameter_value = handle_single_value(field.type_, parameter_value)
            parameter_values.update({field_name: parsed_parameter_value})

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
    if type(input_values) != dict:
        param = class_(value=input_values)
    else:
        param = class_(**input_values)
    return param.get_value_type(), param.get_value()

def build_paramter_block_class(name: str, block_data: dict) -> dict:
    class Config:
        arbitrary_types_allowed = True
    
    class_input = block_data
    class_input.update({"Config": Config})
    block_class = type(name, (BaseModel,), class_input)
    return block_class
