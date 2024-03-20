import importlib
import json
from copy import copy
from inspect import getmembers, getmodule, isclass
from pathlib import Path
from types import ModuleType

from cosmap import locations

"""
This file contains functions for managing analyses. This includes installing, 
uninstalling, and building analysis modules from a path for use in a Cosmap analysis
"""

expected_file_path = Path(__file__).parent / "files.json"
with open(expected_file_path, "r") as f:
    expected_files = json.load(f)
    output = {}
    for key, value in expected_files["files"].items():
        path_key = Path(key)
        output.update({path_key: value})
    expected_files = output


def install_analysis(analysis_path: Path, name=None):
    """
    Install an analysis at the given path, given a particuar name. If the name is not
    specified, it will use the name of the folder the analysis is in.

    Installation does a very basic check that the structure of the analysis folder
    matches what is expected. It does NOT check that an analysis can actually run.
    All that is being done during the actual "installation" is the path to the anlysis
    is being saved.

    """

    verify_analysis_directory(analysis_path)
    if name is None:
        with open(analysis_path / "parameters.json", "r") as f:
            name = json.load(f).get("name", None)
            if name is None:
                name = analysis_path.name
    if name in get_known_analyses():
        raise ValueError(f"Analysis {name} already installed")
    add_new_analyses(analysis_path, name)
    print(f'Analysis "{name}" installed successfully')


def uninstall_analysis(name: str):
    """
    Remove an analysis from the list of know analyses. Just removes the analysis from
    the list of know analyses, assuming it exists.
    """
    if name not in (a := get_known_analyses()):
        raise ValueError(f"Analysis {name} doesn't exist!")
    a.pop(name)
    write_analyses(a)


def verify_analysis_directory(analysis_path: Path, amod: str = None):
    """
    Checks to see that all required files are present in the analysis directory.
    The defintions of the required files are in files.json

    """
    if not analysis_path.is_dir():
        raise ValueError(
            f"Expected a directory for the analysis but found {analysis_path}"
        )
    if not Path.exists(analysis_path):
        raise FileNotFoundError(f"Could not find the analysis path {analysis_path}")

    if amod is not None and not (analysis_path / amod).is_dir():
        raise FileNotFoundError(
            f"Could not find the analysis variant {amod} in {analysis_path}"
        )

    found_files = [f.name for f in analysis_path.glob("*")]
    if amod is not None:
        found_files.append([f.name for f in (analysis_path / amod).glob("*")])

    has_file = [f.name in found_files for f in expected_files]
    missing = []

    for (fname, fdata), found in zip(expected_files.items(), has_file):
        if not found and fdata["required"]:
            missing.append(fname)
    if missing:
        missing = "\n" + "\n".join([m.name for m in missing])
        raise FileNotFoundError(
            f"Could not find the following required files: {missing}"
        )


def get_known_analyses():
    """
    Load the list of known analyses from the known_analyses.json file
    """
    expected_file = locations.here / "analysis" / "known_analyses.json"
    if not expected_file.exists():
        return {}
    else:
        with open(expected_file, "r") as f:
            data = json.load(f)
    return data


def get_analysis_path(name: str):
    """
    Get the path to a particular analysis, given its name
    """
    known_analyses = get_known_analyses()
    if name not in known_analyses:
        raise ValueError(f"Analysis {name} not found!")
    return Path(known_analyses[name]["path"])


def write_analyses(models: dict):
    """
    Write the list of known analyses to the known_analyses.json file
    """
    output_file = locations.here / "analysis" / "known_analyses.json"
    with open(output_file, "w") as f:
        json.dump(models, f)


def add_new_analyses(module_path: Path, model_name: str):
    """
    Add a new analysis to the known_analyses.json file. This is called by
    install_analysis, so all checks for validity have already been done.
    """

    model_data = get_known_analyses()
    model_data.update({model_name: {"path": str(module_path)}})
    write_analyses(model_data)


def load_analysis_files(analysis_name: str, amod: str = None):
    """
    This is a fun one. This function takes the name of an analysis, and returns
    a dictionary of:
        - sub-dictionaries for each json file, with the name being the name of the file
        - a dynamically-created module object, with sub-modules for each python file,
          key name "module"
    """
    if analysis_name not in (a := get_known_analyses()):
        raise ValueError(f"Analysis {analysis_name} not found!")

    analysis_path = Path(a[analysis_name]["path"])
    verify_analysis_directory(analysis_path, amod)

    found_files = load_directory_files(analysis_path, analysis_name)
    missing_jsons = [
        f
        for f in expected_files
        if (
            f.suffix == ".json"
            and f.stem not in found_files
            and expected_files[f]["required"]
        )
    ]
    missing_pythons = [
        f
        for f in expected_files
        if (
            f.suffix == ".py"
            and not hasattr(found_files["module"], f.stem)
            and expected_files[f]["required"]
        )
    ]

    if (missing_jsons or missing_pythons) and amod is None:
        raise FileNotFoundError(
            f"Analysis {analysis_name} is missing" " some required files! \n"
        )

    if amod is not None:
        found_files = combine_with_mod(found_files, analysis_path / amod)
    return found_files


def load_directory_files(directory: Path, name: str) -> dict:
    """
    Loads files in a given directory. This does not do any checking to see if the files
    are valid, or if they are the ones we expect to find. Currently loads json and py
    files. Returns a dictionary.
    """
    found_files = [f.name for f in directory.glob("*")]
    outputs = {}
    module = importlib.machinery.ModuleSpec(name, None)
    module = importlib.util.module_from_spec(module)
    for file in found_files:
        p = directory / file
        if p.suffix == ".json":
            with open(p, "r") as f:
                outputs.update({p.stem: json.load(f)})
        elif p.suffix == ".py":
            file_spec = importlib.util.spec_from_file_location(p.stem, p)
            file_module = importlib.util.module_from_spec(file_spec)
            setattr(module, p.stem, file_module)
            file_spec.loader.exec_module(file_module)
    outputs.update({"module": module})
    return outputs


def combine_with_mod(config_files, amod_directory):
    """
    Combine a base analysis with new behavior/config defined in a variant. This
    function follows the following rules:

    Transformations and transformation definitions will completely overwrite the
    equivalent in the base analysis.

    Configuration will be merged, unless a parameter is defined in both the base
    analysis and the variant. In that case, the variant parameter will overwrite
    the base analysis parameter.

    Plugins will be merged, with the variant plugins taking precedence over the
    base analysis plugins in case of a naming conflict.
    """
    new_files = copy(config_files)
    try:
        amod_files = load_directory_files(amod_directory, amod_directory.name)
        # Load the variant files
    except ValueError:
        raise FileNotFoundError(
            f"No valid files present in analysis variant `{amod_directory.name}`"
            f" at {amod_directory}"
        )

    # Start with transformations, because they're easy.
    transformation_config = amod_files.get("transformations", {})
    transformation_defs = getattr(amod_files["module"], "transformations", None)
    if transformation_defs is not None:
        tdata = combine_transformations(
            new_files["transformations"],
            new_files["module"].transformations,
            transformation_config,
            transformation_defs,
        )
        new_files["transformations"] = tdata[0]
        new_files["module"].transformations = tdata[1]

    # Now, configuration
    if (params := amod_files.get("parameters", None)) is not None:
        if (base_params := config_files.get("parameters", None)) is not None:
            params = combine_dicts(base_params, params)
        else:
            params = params
        new_files["parameters"] = params

    # pydatnic models
    if (defs := getattr(amod_files["module"], "config", None)) is not None:
        base_models = getattr(config_files["module"], "config", None)
        if base_models is not None:
            cfg_models = combine_mods(base_models, defs)
        else:
            cfg_models = defs
        new_files["module"].config = cfg_models
    # Finally, plugins
    plugin_config = amod_files.get("plugins", None)
    plugin_defs = getattr(defs, "plugins", None)
    if all(t is not None for t in [plugin_config, plugin_defs]):
        new_files["plugins"] = combine_dicts(
            config_files.get("plugins", {}), plugin_config
        )
        new_plugin_defs = combine_mods(config_files["module"].plugins, plugin_defs)
        new_files["module"].plugins = new_plugin_defs

    elif not all(t is None for t in [plugin_config, plugin_defs]):
        # One exists, the other doesn't
        raise ValueError(
            "To overwrite plugins, the variant must contain both"
            "a plugins.json file and a plugins.py file"
        )
    return new_files


def combine_transformations(
    left_spec: dict,
    left_impl: ModuleType,
    right_spec: dict = None,
    right_impl: ModuleType = None,
):
    """
    Combine transformations with the following rules:
    - If a transformation is defined in both, the right one takes precedence
    - If a transformation is defined in the right but not the left, it must
      also be defined in the right spec

    Transformation implementations are defind as classes, with static methods
    for the individual transformations.
    """
    if right_impl is None and right_spec is None:
        return left_spec, left_impl
    for block_name, block_impl in getmembers(right_impl):
        if not isclass(block_impl) or block_name.startswith("__"):
            continue

        elif getmodule(block_impl) is not None:
            # Skip imported stuff
            continue
        # simple case, brand new block
        if block_name not in left_spec:
            setattr(left_impl, block_name, block_impl)
            if right_spec is None or not (spec := right_spec.get(block_name, {})):
                raise ValueError(
                    f"Transformation block `{block_name}`" " is not defined in the spec"
                )
            left_spec[block_name] = spec
            continue
        # Block already exists, need to check for new transformations
        for trans_name, trans_impl in block_impl.__dict__.items():
            left_block_impl = getattr(left_impl, block_name)
            left_block_spec = left_spec[block_name]
            right_block_spec = right_spec.get(block_name, {})
            # These should have already been verified to exist
            if trans_name.startswith("__") or not callable(trans_impl):
                continue
            if trans_name not in left_block_spec:
                # New transformation
                if trans_name not in right_block_spec:
                    raise ValueError(
                        f"New transformation {trans_name} " "must have a spec"
                    )
                setattr(left_block_impl, trans_name, trans_impl)
                left_block_spec[trans_name] = right_block_spec[trans_name]
            else:
                setattr(left_block_impl, trans_name, trans_impl)
                if trans_name in right_block_spec:
                    left_block_spec[trans_name] = right_block_spec[trans_name]
    return left_spec, left_impl


def combine_dicts(left: dict, right: dict):
    """
    Combine two dicts recursively. Right takes precedence over left if there
    are key conflicts. If a key is a dictionary in left, it must also be
    a dictionary in right or this method will through an error.
    """
    new_dict = copy(left)
    for key, value in right.items():
        if key not in left:
            new_dict[key] = value
        elif isinstance(value, dict) and isinstance(left[key], dict):
            new_dict[key] = combine_dicts(new_dict.get(key, {}), value)
        elif not isinstance(value, dict) and not isinstance(left[key], dict):
            new_dict[key] = value
        else:
            raise ValueError(f"Cannot combine {left[key]} and {value}")
    return new_dict


def combine_mods(mod_a, mod_b):
    """
    Combines two modules. The second takes precedence over the first.
    This method is not recursive, it only looks a top-level objets.
    """
    for key, value in mod_b.__dict__.items():
        if not key.startswith("__"):
            setattr(mod_a, key, value)
    return mod_a


def combine_pydantic_model(model_a, model_b):
    pass
