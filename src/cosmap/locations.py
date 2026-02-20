from pathlib import Path

import cosmap

here = Path(cosmap.__file__).parents[0]

COSMAP_CONFIG_LOCATION = here / "config"
ROOT = here
