
from pathlib import Path
import json
from cosmap import locations
import importlib

expected_file_path = Path(__file__).parent / "files.json"
with open(expected_file_path, "r") as f:
    expected_files = json.load(f)


def install_analysis(analysis_path: Path, name = None):
    verify_analysis_directory(analysis_path)
    if name is None:
        with open(analysis_path / "parameters.json", "r") as f:
            name = json.load(f).get("name", None)
            if name is None:
                name = analysis_path.name
    if name in get_known_analyses():
        raise ValueError(f"Analysis {name} already installed")
    add_new_analyses(analysis_path, name)

def uninstall_analysis(name: str):
    if name not in (a := get_known_analyses()):
        raise ValueError(f"Analysis {name} doesn't exist!")
    a.pop(name)
    write_analyses(a)

def verify_analysis_directory(analysis_path: Path):
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
    expected_file = locations.here / "analysis" / "known_analyses.json"
    if not expected_file.exists():
        return {}
    else:
        with open(expected_file, "r") as f:
            data = json.load(f)
    return data

def get_analysis_path(name: str):
    known_analyses = get_known_analyses()
    if name not in known_analyses:
        raise ValueError(f"Analysis {name} not found!")
    return Path(known_analyses[name]["path"])

def write_analyses(models: dict):
    output_file = locations.here / "analysis" / "known_analyses.json"
    with open(output_file, "w") as f:
        json.dump(models, f)

def add_new_analyses(module_path: Path, model_name: str):
    model_data = get_known_analyses()
    model_data.update({model_name: {"path": str(module_path)}})
    write_analyses(model_data)

def load_analysis_files(analysis_name):
    if analysis_name not in (a := get_known_analyses()):
        raise ValueError(f"Analysis {analysis_name} not found!")
    

    analysis_path = Path(a[analysis_name]["path"])
    print(analysis_path)
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


def build_analysis_object(base_analysis: str, config: dict, **kwargs):
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
    module = model.get_definition_module(base_analysis)
    transformations = model.get_transformations(base_analysis)
    config.update({"definition_module": module["module"], "definition_path": module["path"]})
    model_block = model.get_model(base_analysis)
    
    block = create_analysis_block("Main", model_block, config)
    block.analysis_parameters.transformations = transformations
    analysis_object = CosmapAnalysis(analysis_paramters=block, **kwargs)
    return analysis_object

