
from pathlib import Path
import json
from cosmap import locations
import importlib


"""
This file contains functions for managing analyses. This includes installing, uninstalling, and building
analysis modules from a path for use in a Cosmap analysis


"""


expected_file_path = Path(__file__).parent / "files.json"
with open(expected_file_path, "r") as f:
    expected_files = json.load(f)

def install_analysis(analysis_path: Path, name = None):
    """
    Install an analysis at the given path, given a particuar name. If the name is not specified, it
    will use the name of the folder the analysis is in.

    Installation does a very basic check that the structure of the analysis folder matches what is
    expected. It does NOT check that an analysis can actually run. All that is being done during
    the actual "installation" is the path to the anlysis is being saved.
    
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
    print(f"Analysis \"{name}\" installed successfully")


def uninstall_analysis(name: str):
    """
    Remove an analysis from the list of know analyses. Just removes the analysis from the list of know analyses,
    assuming it exists.
    """
    if name not in (a := get_known_analyses()):
        raise ValueError(f"Analysis {name} doesn't exist!")
    a.pop(name)
    write_analyses(a)

def verify_analysis_directory(analysis_path: Path):
    """
    Checks to see that all required files are present in the analysis directory.
    The defintions of the required files are in files.json
    
    """
    if not analysis_path.is_dir():
        raise ValueError(f"Expected a directory for the analysis but found {analysis_path}")
    if not Path.exists(analysis_path):
        raise FileNotFoundError(f"Could not find the analysis path {analysis_path}") 
    
    found_files = [f.name for f in analysis_path.glob("*")]
    has_file = [f in found_files for f in expected_files['files']]
    missing = []

    for (fname, fdata), found in zip(expected_files['files'].items(), has_file):
        if not found and fdata["required"]:
            missing.append(fname)
    if missing:
        missing = '\n' + '\n'.join(missing)
        raise FileNotFoundError(f"Could not find the following required files: {missing}")

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

def load_analysis_files(analysis_name):
    """
    This is a fun one. This function takes the name of an analysis, and returns
    a dictionary of:
        - sub-dictionaries for each json file, with the name being the name of the file
        - a dynamically-created module object, with sub-modules for each python file, key name "module"
    """
    if analysis_name not in (a := get_known_analyses()):
        raise ValueError(f"Analysis {analysis_name} not found!")
    

    analysis_path = Path(a[analysis_name]["path"])
    verify_analysis_directory(analysis_path)

    module = importlib.machinery.ModuleSpec(analysis_name, None)
    module = importlib.util.module_from_spec(module)


    outputs = {}
    for file in expected_files["files"]:
        p = analysis_path / file

        if p.exists():
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

