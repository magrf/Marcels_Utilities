import bpy # type: ignore
import os
import json
from typing import Union

__all__ = ["load_json_asset", "refresh_json_asset"]

# Global cache for JSON assets

_json_cache = {}

# JSON file loader helper function

def load_json_asset(filename: str) -> Union[dict, list, None]:
    if filename in _json_cache:
        return _json_cache[filename]
    if os.path.isabs(filename):
        json_path = filename
    else:
        addon_dir = os.path.dirname(__file__)
        json_path = os.path.join(addon_dir, "assets", filename)
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
            _json_cache[filename] = data
            return data
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return None
    
def refresh_json_asset(filename: str) -> Union[dict, list, None]:
    if filename in _json_cache:
        del _json_cache[filename]
    return load_json_asset(filename)