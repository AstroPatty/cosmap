# What is cosmap?

`cosmap` is an engine for asking big questions of big astronomical data. Questions like:  

- How many galaxies should we expect to find in a randomly-selected patch of the sky, out to redshift 1.0?
- How does this number change as the patch of sky gets larger?
- What do their mass profiles look like?
- How does this mass profile evolve over cosmic time?

In short, if your analysis makes use of some large sky survey, like DES, HSC-SSP, or (soon enough) LSST, `cosmap` can help you worry less about managing data and more about designing and interpreting your next-generation analyses.

`cosmap` is built on top of [`heinlein`](https://github.com/PatrickRWells/heinlein), which automates the management and retrieval of survey datasets in your computing environment. In short, if `heinlein` supports it, so does `cosmap`.

# Quickstart

*Note: The following tutorial assumes you have installed `heinlein`, and followed its quickstart to setup access to the CFHTLS catalog.*

`cosmap` can be installed easily with pip:

`>> pip install cosmap`

Navigate somewhere on your machine you don't mind having an extra folder, and initialize a new cosmap analysis:

`>> cosmap init quickstart`

This will create a folder named "quickstart", which should contain the following files:

- config.py
- transformations.py
- parameters.json
- config.py

Don't worry too much about what each of these files is for right this moment, we'll take it one at a time.

#### config.py

This file defines any parameters that will need to be supplied by the user when they run your analysis. `cosmap` uses [`pydantic`](https://github.com/pydantic/pydantic) to validate and manage these parameters. If you're not familiar with `pydantic`, that's alright. For now just copy and paste the following code into the file:

```python
from pydantic import Field, BaseModel
from cosmap.models import SkyCoord, Quantity
from cosmap.config import CosmapAnalysisParameters

class Main(CosmapAnalysisParameters):
    radius: Quantity
    min_radius: Quantity
```

This creates a "block" of analysis parameters, which will be used when we run our analysis.

#### transformations.py

This file defines the transformations that will actually be done on the data given to us by `heinlein.` The only data we'll be requesting for this analysis is catalog data. Don't worry about how we actually go about requesting this data, we'll handle that in a moment. Copy the following code into transformations.py

```python
from astropy.table import Table
import astropy.unts as u
import numpy as np

class Main:
    @staticmethod
        def compute_radius(catalog: Table, sample_region)
	object_coordinates = catalog['coordinates']
	center_coordinate = sample_Region.coordinate
	distances = center_coordinate.separation(object_coordinates)
	catalog['distances'] = distances

    @staticmethod
    def compute_result(catalog: Table, min_radius: u.Quantity)
	mask = catalog['distances'] > min_radius
	filtered_catalog = catalog[mask]	
	n_galaxies = len(filtered_catalog)
	inv = np.sum(filtered_catalog['distances'].to(u.arcsec).value)
	return {"n": n_galaxies, "inv": inv}
```

This set of transformations takes in a catalog of objects in a given field, and computes the sum of the inverse distances from the center of that field to all the objects in the catalog. It filters out objects that are very close to the center of the field, to keep things numerically stable. It also returns the pure number count of galaxies. Are these numbers interesting? Maybe not. But this is what makes `cosmap` so powerful. You can put *absolutely whatever you want in this file.* 

#### transformations.json
Now that we've defined our transformations, let's make sure cosmap actually understand how to use them. The transformations.json file describes the relationship between your transformations, and any other parameters they will need to run. For now, copy and paste the following:

```json
{
    "Main": {
	"compute_radius": {
	    "needed-data": ["catalog"]
	},
	"compute_result" : {
	    "depedencies": {
		"compute_radius": "catalog"
	    },
	    "needed-parameters": ["Main.min_radius"],
		"is-output": true
	}
    }
}
```

This file defines the relationships between your transformations. It specifies a few things.
1. The "compute_radius" transformation requires an input catalog
2. The "compute_result" transformation requires the output of "compute_radius", which will be passed into it as the "catalog" parameter.
3. The "compute_result" transformation also depends on the "min_radius" parameter defined in our "Main" config block.
4. The "compute_radius" transformation should be treated as the output for a given sample.

#### parameters.json

This file defines any config information that your analysis will need, but should not be set by the user. Some of these parameters may be required by `cosmap`, and not specific to your analysis. There's nothing that requires you to put anything in this file. In our case though, we have a couple of things we need to include

```json
{
    "sampling_parameters": {
        "sample_shape": "Circle",
        "sample_dimensions": "@Main.radius"
    },
    "output_parameters": {
        "output_formats": "dataframe",
        "write_format": "csv"
    }
}
```

This tells cosmap that we expect it to give us data from circular regions of the sky, and that the radius of that region can be found in the "Main" parameter block. It also tells cosmap that we will be outputting tabular data. Don't worry that our last transformation doesn't actually return a dataframe. `cosmap` will handle that for us.

#### Install the Analysis
Now we can install the analysis. Navigate to the folder with these files in your terminal, and type the following.

```bash
>> cosmap install .
Analysis "quickstart" installed sucessfully.
```
This will install our analysis

#### Running our analysis

Now that we've defined our analysis, and installed it, let's go ahead and run it and actually see what happens. When running a given analysis, we have to provide it with any configuration that is specific to this run. Navigate to a new folder, and create a json file. You can call it whatever you want, but we'll call it "quickstart_test.json" here. Copy the following contents into it:

```json
{
    "base-analysis": "quickstart",
    "threads": 4,
    "output": "/path/to/output/location.csv",
    "dataset_parameters" : {
        "dataset_name": "cfht"
    },
    "sampling_parameters": {
        "region_type": "Rectangle",
        "region_bounds": {
            "value": [31.0, -11.0, 38, -4],
            "units": "degree"
        },
        "sample_type": "Random",
        "n_samples": 1000

    },
    "radius": {
        "value": 2,
        "units": "arcmin"
    },
    "min_radius" : {
        "value": 5,
        "units": "arcsec"
    }
}
```

Be sure to replace `"/path/to/output/location.csv"` with an actual location on your machine. And if you're working on a machine with less available cores, you may want lower or even delete the "threads" parameter. 

This file defines several things. First, it tells `cosmap` that we want to use the "quickstart" analysis we just installed, and where to put the output. It then tells `cosmap` we're going to sample from a rectangle defined by 31 deg < RA < 38 and -11 < Dec < 4, and that we're looking in the CFHT dataset. We're going to draw random samples from that rectangle, and those samples will be circles with a radius of 2 arcmins.

Running this analysis is simple

`cosmap run quickstart_test.json`

You should get plenty of info about what's going on printed to your screen. A few minutes later, you should see the output file appear on your disk. And a few minutes after that, we'll be done. Take a look at the output. You should see 4 columns. The first two specify the RA and Dec of the center of the given sample. The other two columns are the outputs of our transformation.

## Next Steps
todo!
