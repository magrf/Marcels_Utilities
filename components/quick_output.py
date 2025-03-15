import bpy  # type: ignore
import os
import json
import math
import inspect

from ..utils import load_json_asset, refresh_json_asset

# Helper Functions

def load_output_formats():
    json_path = os.path.join(os.path.dirname(__file__), "..", "properties", "output.json")
    formats = load_json_asset(json_path)
    return formats if formats is not None else {}

def output_preset_items(self, context):
    formats_dict = load_output_formats()
    items = []
    for key, data in formats_dict.items():
        display = data.get("display_name", key)
        items.append((key, display, f"Output format: {display}"))
    if not items:
        items.append(("None", "None", "No output formats found"))
    return items

def apply_exr_settings(scene, data, props, context):
    scene.render.image_settings.color_depth = data.get("color_depth", "16")
    scene.render.image_settings.exr_codec = data.get("exr_codec", "ZIP")
    passes_dict = data.get("passes", {})

    view_layer = context.view_layer
    if not view_layer:
        return False

    if hasattr(view_layer, "use_pass_cryptomatte_object"):
        view_layer.use_pass_cryptomatte_object = passes_dict.get("cryptomatte_object", False) and props.use_cryptomatte
    if hasattr(view_layer, "use_pass_cryptomatte_material"):
        view_layer.use_pass_cryptomatte_material = passes_dict.get("cryptomatte_material", False) and props.use_cryptomatte
    if hasattr(view_layer, "cycles") and hasattr(view_layer.cycles, "use_pass_shadow_catcher"):
        view_layer.cycles.use_pass_shadow_catcher = props.use_shadow_catcher
    else:
        print("Active view layer does not support 'shadow_catcher' pass in cycles settings.")
    if hasattr(view_layer, "use_pass_ambient_occlusion"):
        view_layer.use_pass_ambient_occlusion = passes_dict.get("ambient_occlusion", False) and props.use_ambient_occlusion
    else:
        print("Active view layer does not support 'ambient_occlusion' pass.")

    if hasattr(view_layer, "cycles"):
        if hasattr(view_layer.cycles, "use_pass_denoising_data"):
            view_layer.cycles.use_pass_denoising_data = passes_dict.get("denoising_data", False)
        if hasattr(view_layer.cycles, "denoising_store_passes"):
            view_layer.cycles.denoising_store_passes = passes_dict.get("denoising_store_passes", False)
        if hasattr(view_layer.cycles, "pass_debug_sample_count"):
            view_layer.cycles.pass_debug_sample_count = passes_dict.get("pass_debug_sample_count", False)
        if hasattr(view_layer.cycles, "use_pass_volume_direct"):
            view_layer.cycles.use_pass_volume_direct = passes_dict.get("volume_direct", False)
        if hasattr(view_layer.cycles, "use_pass_volume_indirect"):
            view_layer.cycles.use_pass_volume_indirect = passes_dict.get("volume_indirect", False)
    else:
        print("Active view layer does not have cycles settings.")

    special_keys = {
        "cryptomatte_object", "cryptomatte_material",
        "shadow_catcher", "ambient_occlusion",
        "denoising_data", "sample_count", "volume_direct", "volume_indirect",
        "denoising_store_passes", "pass_debug_sample_count"
    }
    for pass_key, pass_val in passes_dict.items():
        if pass_key in special_keys:
            continue
        prop_name = "use_pass_" + pass_key
        if hasattr(view_layer, prop_name):
            setattr(view_layer, prop_name, pass_val)
    return True

def apply_png_settings(scene, data):
    scene.render.image_settings.color_mode = data.get("color_mode", "RGBA")
    cd = str(data.get("color_depth", 8))
    scene.render.image_settings.color_depth = cd
    scene.render.image_settings.compression = data.get("compression", 15)

def apply_jpeg_settings(scene, data):
    scene.render.image_settings.color_mode = data.get("color_mode", "RGB")
    scene.render.image_settings.quality = data.get("quality", 90)

def apply_ffmpeg_settings(scene, data):
    scene.render.image_settings.color_mode = data.get("color_mode", "RGB")
    scene.render.ffmpeg.format = data.get("ffmpeg_format", "MPEG4")

# Operator

class OUTPUT_OT_ApplyPreset(bpy.types.Operator):
    """Apply the selected output preset from output.json."""
    bl_idname = "output.apply_output_preset"
    bl_label = "Apply Output Preset"

    def execute(self, context):
        scene = context.scene
        props = scene.output_preset_props
        formats_dict = load_output_formats()
        chosen_key = props.output_preset_tag
        if chosen_key not in formats_dict:
            self.report({'WARNING'}, f"No output format found for: {chosen_key}. Using default 'exr'.")
            chosen_key = "exr"
        data = formats_dict.get(chosen_key, {"file_format": "OPEN_EXR_MULTILAYER", "display_name": "OpenEXR MultiLayer"})
        file_format = data.get("file_format", "OPEN_EXR_MULTILAYER")
        scene.render.image_settings.file_format = file_format

        if file_format == "OPEN_EXR_MULTILAYER":
            if not apply_exr_settings(scene, data, props, context):
                self.report({'WARNING'}, "No active view layer found. EXR settings not fully applied.")
        elif file_format == "PNG":
            apply_png_settings(scene, data)
        elif file_format == "JPEG":
            apply_jpeg_settings(scene, data)
        elif file_format == "FFMPEG":
            apply_ffmpeg_settings(scene, data)

        display_name = data.get("display_name", chosen_key)
        self.report({'INFO'}, f"Applied Output Preset: {display_name}")
        return {'FINISHED'}

# Property Group

class OutputPresetProperties(bpy.types.PropertyGroup):
    output_preset_tag: bpy.props.EnumProperty(
        name="Output Preset",
        description="Select the output preset",
        items=output_preset_items
    ) # type: ignore
    use_cryptomatte: bpy.props.BoolProperty(
        name="Cryptomatte",
        description="Enable cryptomatte passes if the JSON also has them enabled",
        default=True
    ) # type: ignore
    use_ambient_occlusion: bpy.props.BoolProperty(
        name="Ambient Occlusion",
        description="Enable AO pass if the JSON also has it enabled",
        default=True
    ) # type: ignore
    use_shadow_catcher: bpy.props.BoolProperty(
        name="Shadow Catcher",
        description="Enable shadow catcher pass if the JSON also has it enabled",
        default=True
    ) # type: ignore

# Panel

class OUTPUT_PT_PresetPanel(bpy.types.Panel):
    bl_label = "Output Presets"
    bl_idname = "OUTPUT_PT_preset_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "output"
    bl_order = -1000
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.output_preset_props
        layout.prop(scene.render, "filepath", text="")
        layout.prop(props, "output_preset_tag", text="Format")
        if props.output_preset_tag == "exr":
            row = layout.row(align=True)
            row.label(text="\t\t\t\t\t\t\t\tShadow Catcher:")
            row.prop(props, "use_shadow_catcher", text="")
            row = layout.row(align=True)
            row.label(text="\t\t\t\t\t\t\t\tAmbient Occlusion:")
            row.prop(props, "use_ambient_occlusion", text="")
            row = layout.row(align=True)
            row.label(text="\t\t\t\t\t\t\t\tCryptomatte:")
            row.prop(props, "use_cryptomatte", text="")
        layout.operator("output.apply_output_preset", text="Apply Preset", icon='OUTPUT')

# Registration

classes = [
    OUTPUT_OT_ApplyPreset,
    OutputPresetProperties,
    OUTPUT_PT_PresetPanel,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.output_preset_props = bpy.props.PointerProperty(type=OutputPresetProperties)

def unregister():
    del bpy.types.Scene.output_preset_props
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
