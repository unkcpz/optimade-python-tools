""" Test Data to be used with the OPTIMADE server """
import bson.json_util
from typing import Dict, Any
from pathlib import Path


data_paths = {
    "structures": "test_structures.json",
    "references": "test_references.json",
    "links": "test_links.json",
    "providers": "providers.json",
}

structures: Dict[str, Any]
references: Dict[str, Any]
providers: Dict[str, Any]
links: Dict[str, Any]

for var, path in data_paths.items():
    try:
        with open(Path(__file__).parent / path) as f:
            globals()[var] = bson.json_util.loads(f.read())

        if var == "structures":
            globals()[var] = sorted(globals()[var], key=lambda x: x["task_id"])
    except FileNotFoundError:
        if var != "providers":
            raise
