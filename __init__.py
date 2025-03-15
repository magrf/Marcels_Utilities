bl_info = {
    "name": "Marcels Utilities",
    "author": "Marcel Graf",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "3D View > Tool Shelf",
    "description": "Collection of Blender Utilities",
    "warning": "",
    "tracker_url": "https://github.com/magrf/Marcels_Utilities",
    "category": "Utility",
    "license": ["SPDX:GPL-3.0-or-later"],
}

import bpy # type: ignore
from .components import quick_hdri

def register():
    quick_hdri.register()

def unregister():
    quick_hdri.unregister()

if __name__ == "__main__":
    register()