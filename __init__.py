bl_info = {
    "name": "met[ads] Screen Presets",
    "author": "Marcel Graf <marcel@met-ads.com>",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "3D View > Tool Shelf",
    "description": "Streamlined Set-Up for OOH Screens by met[ads]",
    "warning": "",
    "wiki_url": "https://github.com/marcelmetads/met-ads-Screen-Presets/wiki",
    "tracker_url": "https://github.com/marcelmetads/met-ads-Screen-Presets",
    "category": "Render",
    "tags": ["Screen Setup", "Preset"],
    "license": ["SPDX:GPL-3.0-or-later"],
}

import bpy # type: ignore
from . import properties, panels, scene_preset, render_preset, output_preset, hdri_preset

def register():
    properties.register()
    scene_preset.register()
    render_preset.register()
    output_preset.register()
    hdri_preset.register()
    panels.register()

def unregister():
    panels.unregister()
    scene_preset.unregister()
    render_preset.unregister()
    output_preset.unregister()
    hdri_preset.unregister()
    properties.unregister()

if __name__ == "__main__":
    register()