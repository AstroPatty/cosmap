from __future__ import annotations

import toml
from abc import ABC, abstractmethod
from astropy import units
import pathlib
import json
from copy import copy
from functools import singledispatchmethod, partial
from pathlib import Path


from cosmap.locations import MAIN_CONFIG_DIR
from cosmap.config import custom
from cosmap.config import utils

def load_base_config():
    base_param_path =  Path(MAIN_CONFIG_DIR / "base_analysis_params.json")
    block = ParameterBlock.read_template(base_param_path)
    return block

def reject_change(msg, *args, **kwargs):
    raise CosmapParameterException(msg)

def reject_overwritten_change(event, pname, bname, *args, **kwargs):
    msg = f"Parameter {pname} has been linked to block {bname} and cannot be changed!"
    reject_change(msg, *args, **kwargs)


class CosmapParameterException(Exception):
    pass

def build_block(specification: dict, parameters: dict, name = "main"):
    """
    This function takes in a specification for a paramater block and the 
    parameters that have actually been provided and turns them into an actual
    ParameterBlock. This will throw an error if a parameter that is
    marked as required in the specification is not found in the provided
    parameters. Parameters are assumed to be required unless marked otherwise
    OR provided with a default value. 

    This function will also throw an error if the structure of the two
    dictionaries does not match. In other words, any parameter blocks
    (or subblocks) that are in the specification should be in the
    associated parameter dictionary. Subblocks will be parsed
    recursively.
    """
    specification_blocks = set([k for k, v in specification.items() if v.get("type", "parameter") == "block"])
    parameter_blocks = set([k for k, v in parameters.items() if v.get("type", "parameter") == "block"])
    if specification_blocks != parameter_blocks:
        assymetry = list(specification_blocks.symmetric_difference(parameter_blocks))
        failure_string = ", ".join(assymetry)
        raise CosmapParameterException(f"Paramter block {name} doesn't match its specification: "\
                                       f"Found mismatching blocks {failure_string}")
    output = {}
    for key, value in specification.items():
        value_type = value.get("type", "parameter")
        if value_type == "block":
            block = build_block(value, parameters[value], key)
            output.update({key: block})
        if value_type == "parameter":
            parameter = utils.build_paramter()



class ParameterBlock:
    def __init__(self, name, params: dict, *args, **kwargs):
        """
        Parameter blocks keep track of configuration. They
        are built on top of the "param" library.

        Includes a plugin system that allows for parameters
        not allowed by the library. They include allow astronomical units,
        and letting a parameter be either a single value, or a list of values
        of the given type. See cosmap.config.custom

    
        In general, these are meant to be read from configuration files,
        not edited directly at runtime. Template files are written in json,
        while implmentations are written in toml.
        
        Parameter blocks are recursive, and can contain sub-blocks, each
        of which can contain its own sub-blocks, etc. Sub-blocks are denoted
        by capitalized names, while parameters must be lower-case.


        Parameters and sub-blocks can be accessed by indexing:

        subblock = ParamBlockObject["Analysis"]
        param_value = ParamBlockObject["parameter_a"]

        For examples of templates, see cosmap/analyses
        """
        self.name = name
        self.dependencies = {}

        self.initialize(params, *args, **kwargs)

    def __getattr__(self, key: str):
        """
        Checks for blocks first, then for parameters.
        If a parameter is reqired but has not yet
        been set, throw an error"
        """
        if (block := self._sub_blocks.get(key, False)):
            return block
        elif key in self.constants:
            return getattr(self._params, key)
        elif key in self.dependencies:
            return self.dependencies[key]

        elif (pdata := self.param_attributes.get(key)):
            if (not self._params or 
                (pdata.get("required", False) and not pdata.get("set", False))):
                raise CosmapParameterException(f"Parameter {key} has not been set yet.")

        else: raise CosmapParameterException(f"This block does not have a parameter or a sub-block named {key}.")

        return getattr(self._params, key)

    def __getstate__(self):
        return self.__dict__


    def __setstate__(self, data):
        self.__dict__ = data

    @property
    def subblocks(self):
        return self._sub_blocks

    def set_overwrites(self, other: ParameterBlock, *args, **kwargs):
        """
        Searches a second parameter block for parameters in this block. If/when
        they are found, set the value in this block to the value found in the second
        block. The parameter in this block will be updated if the parameter in the
        second block changes.

        Parameters in the second block should be constants. Constants can be declared
        with a simple key-value pair.
        """
        self._handle_overwrites(other)

        my_subblock_names = set(self._sub_blocks.keys())
        other_subblock_names = set(other._sub_blocks.keys())
        shared_subblocks = my_subblock_names.intersection(other_subblock_names) - {"Plugins"}
        if shared_subblocks:
            for sb in shared_subblocks:
                self._sub_blocks[sb].set_overwrites(other[sb])

    def _handle_overwrites(self, other: ParameterBlock):
        my_param_names = set(self._params.param.values().keys())
        other_param_names = set(other._params.param.values().keys())
        shared_params = my_param_names.intersection(other_param_names)
        shared_params = shared_params - {"name", "version", "Plugins"}
        for param in shared_params:
            if not other._params.param[param].constant:
                raise CosmapParameterException("Values for overwritten parameters must be constant!")
            other_param_value = other[param]
            self.set_values({param: other_param_value})
            rejection = partial(reject_overwritten_change, pname = param, bname = other.name)
            self._params.param.watch(rejection, [param])

    def attach_dependencies(self, other: ParameterBlock, *args, **kwargs):
        """
        Searches through a parameter block (or any sub-blocks) for a "depends-on" parameter.
        This parameter will reference parameters in this block that it needs a reference to.
        This function will attach those referenced parameters to the other block.
        """
        try:
            dependencies = other["depends-on"]

        except CosmapParameterException:
            for sb in other._sub_blocks.values():
                self.attach_dependencies(sb)
            return

        all_dependencies = {}
        for dependency in dependencies:
            param_path = dependency.split(".")
            val = self[param_path[0]]
            for pp in param_path[1:]:
                val = val[pp]
            all_dependencies.update({pp: val})
        other.add_dependencies(all_dependencies)

    def add_dependencies(self, dependencies):
        for dep, val in dependencies.items():
            if dep in self._params.param.values().keys():
                raise CosmapParameterException("Can't add a dependency because this parameter always exists!")
            self.dependencies.update({dep: val})      
        

    def initialize(self, params, *args, **kwargs):
        self.param_attributes = {}
        self.doc = params.pop("doc", False)
        self.initialize_blocks(params, *args, **kwargs)
        self.check_for_constants(params, *args, **kwargs)
        self.remove_special_keywords(params)
        self.initialize_block(params)

    def __getitem__(self, key):
        return self.__getattr__(key)
    
    def __setitem__(self, key, value):
        self.set_values({key: value})

    @classmethod
    def read_template(cls, template_path: pathlib.Path):
        with open(template_path, "r") as f:
            data = json.load(f)
        name = data.pop("name", None)
        return cls(name, data)
    
    def set_block(self, values: dict | ParameterBlock, missing = "skip"):
        """
        Sets values sub-blocks for the block"
        """
        if type(values) == dict:
            sub_blocks = {k: v for k,v in values.items() if k[0].isupper()}
            params = {k: v for k,v in values.items() if k not in sub_blocks.keys()}
            for k, sb in sub_blocks.items():
                self.set_sub_block(k, sb)
            self.set_values(params)
            
    def check_for_constants(self, params, *args, **kwargs):
        constants = [pname for pname, pval in params.items() if type(pval) != dict]
        self.constants = {}
        for const in constants:
            value = params.pop(const)
            self.constants.update({const: value})

    def add_sub_block(self, name: str, block, *args, **kwargs):
        """
        Adds a sub-block, throws an error if it already exits.
        """
        if not self._sub_blocks.get(name, False):
            self._sub_blocks.update({name: block})
        else:
            raise CosmapParameterException(f"Sub-block {name} already exists in this block!")
    
    def pop_sub_block(self, name: str):
        if not (sb := self._sub_blocks.pop(name, False)):
            raise CosmapParameterException(f"Sub-block {name} does not exist!")
        return sb


    @singledispatchmethod
    def set_sub_block(self, block_name: str, values):
        """
        Sets values for a sub-block. Throws an error if 
        it does NOT already exist
        """
        try:
            block = self._sub_blocks[block_name]
        except KeyError:
            raise CosmapParameterException(f"Tried to set values for the block {block_name} but this block does not exist inside block {self.name}")
        self._sub_blocks[block_name].set_block(values)


    
    def set_values(self, items: dict):
        """
        Sets values for a set of parameters.
        """
        for k, v in items.items():
            value = self.apply_value_plugins(k, v)
            try:
                self.param_attributes[k]["set"] = True
            except KeyError:
                self.param_attributes[k] = {"set": True}
            setattr(self._params, k, value)
    

    def remove_special_keywords(self, params: dict, *args, **kwargs):
        """
        Removes special keywords that cannot be interpreted by the 
        param library.
        """
        take_out = ["allow_multiple", "required", "type"] + list(self.plugins.keys())
        parsed = {}
        for p, param_data in params.items():
            param_attributes = {a: param_data.pop(a) for a in take_out if a in param_data.keys()}
            parsed.update({p: param_attributes})
        self.param_attributes.update(parsed)
        
    def initialize_blocks(self, params: dict, *args, **kwargs):
        """
        Initializes the sub-blocks, based on a dictionary
        typically read from a configuration file. 
        """
        self._sub_blocks = {}
        self.initialize_plugins(params, *args, **kwargs)
        block_names = [k for k in params.keys() if k[0].isupper()]
        for bn in block_names:
            block = ParameterBlock(bn, params.pop(bn), Parameter_plugins = self.plugins)
            self.add_sub_block(bn, block)

    def initialize_plugins(self, params: dict, *args, **kwargs):
        """
        Initializes any plugins required to parse the configuration
        file (such as units)
        """
        plugins = params.get("Plugins", False)
        if (passed := kwargs.pop("Parameter_plugins", False)):
            self.plugins = passed
            return
        self.plugins = {}
        if plugins and (param_plugins := plugins.get("Parameters", False)):
            for name, plugin in param_plugins.items():
                plugin_cls = getattr(custom, plugin)
                self.plugins.update({name: plugin_cls()})
    def initialize_block(self, params):
        pars = {}
        for name, pdata in self.param_attributes.items():
            if not pdata:
                continue
            ptype = getattr(param, pdata['type'])
            par = ptype(**params[name])
            par = self.apply_template_plugins(par, self.param_attributes[name])
            if pdata.get("allow_multiple", False):
                par = custom.listOrSingleParam(par)
            pars.update({name: par})
        for constant, value in self.constants.items():
            par = param.Parameter(value, constant=True)
            pars.update({constant: par})
        self._pclass = type(self.name, (param.Parameterized,), pars)
        self._params = self._pclass()

    def apply_template_plugins(self, par, pdata):
        """
        Apply a plugin to a template. The plugin may interpret
        extra data passed with the parameter. Returns
        a param.Parameter object.
        """
        newpar = par
        for key, value in pdata.items():
            if key in self.plugins.keys():
                newpar = self.plugins[key].parse_template(newpar, value)
        return newpar
    
    def apply_value_plugins(self, name, pardata):
        """
        Apply a plugin to values passed in for an implementation
        of a given analysis. For example, handles units. 
        """
        if type(pardata) != dict:
            return pardata
        
        value = pardata.pop("value")
        for name, plugin in self.plugins.items():
            if name in pardata.keys():
                value = plugin.parse_value(value, **pardata)
        return value


class CosmapParameters:
    base_config = load_base_config()
    def __init__(
        self,
        base_analysis_config: Path | ParameterBlock,
        analysis_config_data: dict):
        """
        The CosmapParameters object is the top-level configuration
        management object. It understand how to resolve conflicts
        between specific parameter blocks, and behaves (largely) like
        a parameter block to the end user.
        """
        self.config = copy(self.base_config)
        self.reconcile_base_analysis_config(base_analysis_config)
        self.load_analysis_config(analysis_config_data)
        self.config.attach_dependencies(self.base_anlysis_config)
        self.config.add_sub_block("Analysis", self.base_anlysis_config)

    def __getitem__(self, __key):
        return self.config[__key]

    def reconcile_base_analysis_config(self, base_analysis_config, *args, **kwargs):
        """
        Loads the base analysis config (if necessary). And reconcicles it with the base
        config.
        """
        try:
            p = Path(base_analysis_config)
            base_analysis_config_block = ParameterBlock.read_template(p)
        except TypeError:
            base_analysis_config_block = base_analysis_config


        self.config.set_overwrites(base_analysis_config_block)
        self.base_anlysis_config = base_analysis_config_block
    
    def load_analysis_config(self, analysis_config_data, *args, **kwargs):
        analysis_config = analysis_config_data.pop("Analysis")
        self.base_anlysis_config.set_block(analysis_config)
        self.config.set_block(analysis_config_data)


    def load_analysis_plugins(self, plugins, *args, **kwargs):
        pass