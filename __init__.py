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
from .components import quick_hdri, quick_output

def register():
    quick_hdri.register()
    quick_output.register()

def unregister():
    quick_hdri.unregister()
    quick_output.register()

if __name__ == "__main__":
    register()