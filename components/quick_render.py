import bpy  # type: ignore
import os
import json
import math
import inspect
import shutil

from bpy.props import BoolProperty, PointerProperty, StringProperty
from bpy.types import Operator, Panel, PropertyGroup, Menu
# Use an absolute import (adjust the module path to match your add-on structure)
from ..utils import load_json_asset, refresh_json_asset

# --- Helper Functions ---

def load_render_presets():
    json_path = os.path.join(os.path.dirname(__file__), "..", "properties", "render.json")
    presets = load_json_asset(json_path)
    return presets if presets is not None else []

def apply_cycles_render_settings(scene, render_preset_data, props):
    scene.cycles.adaptive_threshold = float(render_preset_data.get("noise_thresh", 0.01))
    scene.cycles.samples = int(render_preset_data.get("samples", 512))
    scene.cycles.time_limit = float(render_preset_data.get("time", 0.0))
    
    # Apply selected denoiser settings from the panel
    denoiser = props.denoiser_type
    scene.cycles.denoiser = denoiser
    if denoiser == "OPTIX":
        scene.cycles.use_denoising = True
    elif denoiser == "OPENIMAGEDENOISE":
        scene.cycles.denoising_quality = props.denoiser_quality
        scene.cycles.denoising_use_gpu = props.denoiser_use_gpu

    scene.render.use_persistent_data = render_preset_data.get("persistent_data", True)
    scene.cycles.use_auto_tile = render_preset_data.get("use_tiling", True)
    scene.cycles.filter_width = float(render_preset_data.get("filter_width", 1.0))
    scene.render.film_transparent = render_preset_data.get("transparent", True)

def apply_workbench_render_settings(scene, render_preset_data):
    scene.render.film_transparent = render_preset_data.get("transparent", True)
    shading = bpy.context.scene.display.shading
    shading.light = render_preset_data.get("lighting", "STUDIO").upper()
    shading.color_type = render_preset_data.get("color_type", "MATERIAL").upper()
    shading.show_cavity = bool(render_preset_data.get("show_cavity", True))
    shading.cavity_type = render_preset_data.get("cavity_type", "BOTH").upper()

def apply_resolution_tile_settings(scene, render_preset_data, preset_engine):
    preset_multiplier = float(render_preset_data.get("render_percentage", 1.0))
    current_percentage = scene.render.resolution_percentage or 100
    final_res = int(current_percentage * preset_multiplier)
    scene.render.resolution_percentage = final_res

    width = scene.render.resolution_x
    height = scene.render.resolution_y
    if (width / height > 2) or (height / width > 2):
        target = min(width, height)
    else:
        target = max(width, height)
    tile_size = 2 ** round(math.log(target, 2))
    if preset_engine == "CYCLES":
        scene.cycles.tile_size = int(tile_size)

def preset_differs(scene, preset_data):
    """Return True if the current scene settings (excluding denoiser settings) differ from the preset."""
    s = scene
    diff = False
    if abs(s.cycles.adaptive_threshold - float(preset_data.get("noise_thresh", 0.01))) > 1e-6:
        diff = True
    elif s.cycles.samples != int(preset_data.get("samples", 512)):
        diff = True
    elif abs(s.cycles.time_limit - float(preset_data.get("time", 0.0))) > 1e-6:
        diff = True
    elif abs((s.render.resolution_percentage or 100) - int(float(preset_data.get("render_percentage", 1.0)) * 100)) > 1e-6:
        diff = True
    elif s.render.use_persistent_data != preset_data.get("persistent_data", True):
        diff = True
    elif s.cycles.use_auto_tile != preset_data.get("use_tiling", True):
        diff = True
    elif abs(s.cycles.filter_width - float(preset_data.get("filter_width", 1.0))) > 1e-6:
        diff = True
    elif s.render.film_transparent != preset_data.get("transparent", True):
        diff = True
    return diff

# --- Operator to Apply Render Preset ---

class RENDER_OT_apply_render_preset(bpy.types.Operator):
    """Apply a render preset from the JSON file."""
    bl_idname = "render.apply_render_preset"
    bl_label = "Apply Render Preset"

    def execute(self, context):
        scene = context.scene
        props = scene.render_preset_props
        render_presets = load_render_presets()
        render_preset_data = None
        # Use the stored preset name (display name) to lookup the preset
        for p in render_presets:
            if p.get("display_name") == props.render_preset_tag:
                render_preset_data = p
                break
        if render_preset_data is None:
            self.report({'WARNING'}, f"No render preset found for preset: {props.render_preset_tag}")
            return {'CANCELLED'}

        preset_engine = render_preset_data.get("engine", "CYCLES").upper()
        scene.render.engine = preset_engine

        if preset_engine == "CYCLES":
            apply_cycles_render_settings(scene, render_preset_data, props)
        elif preset_engine == "BLENDER_WORKBENCH":
            apply_workbench_render_settings(scene, render_preset_data)

        apply_resolution_tile_settings(scene, render_preset_data, preset_engine)

        self.report({'INFO'}, f"Applied Render Preset: {props.render_preset_tag}")
        return {'FINISHED'}

# --- Operator to Select a Render Preset from Menu ---

class RENDER_OT_select_render_preset(bpy.types.Operator):
    bl_idname = "render.select_render_preset"
    bl_label = "Select Render Preset"
    preset_value: StringProperty()

    def execute(self, context):
        context.scene.render_preset_props.render_preset_tag = self.preset_value
        return {'FINISHED'}

# --- Menu for Render Presets ---

class RENDER_MT_render_preset_menu(bpy.types.Menu):
    bl_label = "Select Render Preset"
    bl_idname = "RENDER_MT_render_preset_menu"

    def draw(self, context):
        layout = self.layout
        presets = load_render_presets()
        for preset in presets:
            value = preset.get("display_name", "Unknown")
            op = layout.operator("render.select_render_preset", text=value)
            op.preset_value = value

# --- Operator to Save Render Preset ---

class RENDER_OT_save_render_preset(bpy.types.Operator):
    bl_idname = "render.save_render_preset"
    bl_label = "Save Render Preset"
    bl_description = "Save the current render settings as a new preset"

    preset_name: StringProperty(name="Name", default="")

    def invoke(self, context, event):
        self.bl_label = "Save Render Preset"
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "preset_name", text="Name")

    def execute(self, context):
        scene = context.scene
        new_entry = {
            "display_name": self.preset_name,
            "noise_thresh": scene.cycles.adaptive_threshold,
            "samples": scene.cycles.samples,
            "time": scene.cycles.time_limit,
            "render_percentage": (scene.render.resolution_percentage or 100) / 100.0,
            "engine": scene.render.engine,
            "device": scene.cycles.device,
            "persistent_data": scene.render.use_persistent_data,
            "use_tiling": scene.cycles.use_auto_tile,
            "filter_width": scene.cycles.filter_width,
            "transparent": scene.render.film_transparent
        }
        addon_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
        json_path = os.path.join(addon_dir, "properties", "render.json")
        try:
            if os.path.isfile(json_path):
                with open(json_path, 'r') as f:
                    data = json.load(f)
            else:
                data = []
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load JSON: {e}")
            return {'CANCELLED'}
        data.append(new_entry)
        try:
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to save JSON: {e}")
            return {'CANCELLED'}

        refresh_json_asset(json_path)
        scene.render_preset_props.render_preset_tag = new_entry["display_name"]
        # Force redraw of all Properties areas so the menu refreshes immediately.
        for area in bpy.context.screen.areas:
            if area.type == 'PROPERTIES':
                area.tag_redraw()
        self.report({'INFO'}, f"Render Preset saved: {self.preset_name}")
        return {'FINISHED'}

# --- Property Group ---

class RenderPresetProperties(bpy.types.PropertyGroup):
    # We now use a StringProperty to store the preset name.
    render_preset_tag: StringProperty(
        name="Preset",
        description="Name of the render preset",
        default=""
    )
    denoiser_type: bpy.props.EnumProperty(
        name="Denoiser",
        description="Choose a denoiser",
        items=[
            ("OPTIX", "OptiX", "Use OptiX denoiser"),
            ("OPENIMAGEDENOISE", "OpenImageDenoise", "Use OpenImageDenoise")
        ],
        default="OPTIX"
    )
    denoiser_quality: bpy.props.EnumProperty(
        name="Quality",
        description="Select denoiser quality",
        items=[
            ("LOW", "Low", "Low quality denoising"),
            ("MEDIUM", "Medium", "Medium quality denoising"),
            ("HIGH", "High", "High quality denoising")
        ],
        default="HIGH"
    )
    denoiser_use_gpu: bpy.props.BoolProperty(
        name="Use GPU",
        description="Enable GPU acceleration for OpenImageDenoise",
        default=True
    )

# --- Panel ---

class RENDER_PT_RenderPresetPanel(bpy.types.Panel):
    bl_label = "Render Presets"
    bl_idname = "RENDER_PT_render_preset_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"
    bl_order = -1000

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.render_preset_props

        row = layout.row(align=True)
        row.menu("RENDER_MT_render_preset_menu", text=(props.render_preset_tag or "Select Preset"))
        # Only show denoiser options if the selected preset uses Cycles.
        preset_data = None
        for p in load_render_presets():
            if p.get("display_name") == props.render_preset_tag:
                preset_data = p
                break
        if preset_data and preset_data.get("engine", "").upper() == "CYCLES":
            layout.prop(props, "denoiser_type")
            if props.denoiser_type == "OPENIMAGEDENOISE":
                layout.prop(props, "denoiser_quality")
                layout.prop(props, "denoiser_use_gpu")
            if preset_differs(scene, preset_data):
                row.operator("render.save_render_preset", text="", icon="FILE_TICK")
        layout.operator("render.apply_render_preset", text="Apply Render Preset", icon='SCENE')

# --- Registration ---

classes = [
    RENDER_OT_apply_render_preset,
    RENDER_OT_save_render_preset,
    RENDER_OT_select_render_preset,
    RenderPresetProperties,
    RENDER_MT_render_preset_menu,
    RENDER_PT_RenderPresetPanel,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.render_preset_props = bpy.props.PointerProperty(type=RenderPresetProperties)

def unregister():
    del bpy.types.Scene.render_preset_props
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()