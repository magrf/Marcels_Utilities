import bpy  # type: ignore
import os
import math
import json
import shutil

from bpy.props import EnumProperty, FloatProperty, StringProperty, PointerProperty  # type: ignore
from bpy.types import Operator, Panel, PropertyGroup # type: ignore
from ..utils import load_json_asset, refresh_json_asset

# Operator Functions

def setup_world_nodes(hdri_path, mapping_rotation_deg=0.0, strength=1.0):
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    for img in list(bpy.data.images):
        if img.filepath.lower().endswith(".exr"):
            bpy.data.images.remove(img)
    tex_coord_node = nodes.new('ShaderNodeTexCoord')
    mapping_node = nodes.new('ShaderNodeMapping')
    # Removed fixed name assignment
    env_tex_node = nodes.new('ShaderNodeTexEnvironment')
    background_node = nodes.new('ShaderNodeBackground')
    world_out_node = nodes.new('ShaderNodeOutputWorld')
    tex_coord_node.location = (-800, 0)
    mapping_node.location = (-600, 0)
    env_tex_node.location = (-400, 0)
    background_node.location = (-100, 0)
    world_out_node.location = (200, 0)
    links.new(tex_coord_node.outputs['Generated'], mapping_node.inputs['Vector'])
    links.new(mapping_node.outputs['Vector'], env_tex_node.inputs['Vector'])
    links.new(env_tex_node.outputs['Color'], background_node.inputs['Color'])
    links.new(background_node.outputs['Background'], world_out_node.inputs['Surface'])
    if os.path.isfile(hdri_path):
        env_tex_node.image = bpy.data.images.load(hdri_path)
    else:
        print("HDRI file not found:", hdri_path)
    mapping_node.inputs["Rotation"].default_value[2] = math.radians(mapping_rotation_deg)
    background_node.inputs["Strength"].default_value = strength

class HDRI_OT_Apply(Operator):
    bl_idname = "hdri.apply"
    bl_label = "Apply HDRI"
    bl_description = "Apply the selected HDRI to the world environment"

    def execute(self, context):
        props = context.scene.hdri_props
        hdri_file = props.hdri_preset
        addon_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
        if hdri_file == "CUSTOM":
            custom_path = props.custom_hdri_filepath
            if not custom_path or not os.path.isfile(custom_path):
                self.report({'ERROR'}, "No valid custom HDRI file specified.")
                return {'CANCELLED'}
            final_mapping_deg = 0
            props.hdri_base_rotation = final_mapping_deg
            props.hdri_rotation_offset = 0
            hdri_path = custom_path
            setup_world_nodes(hdri_path, mapping_rotation_deg=final_mapping_deg)
            self.report({'INFO'}, f"Custom HDRI applied: {custom_path}")
            return {'FINISHED'}
        json_path = os.path.join(os.path.dirname(__file__), "..", "properties", "hdri.json")
        hdri_data = load_json_asset(json_path)
        selected = next((e for e in hdri_data if e.get("file") == hdri_file), None)
        if not selected:
            self.report({'ERROR'}, "Selected HDRI not found.")
            return {'CANCELLED'}
        final_mapping_deg = 0
        props.hdri_base_rotation = final_mapping_deg
        props.hdri_rotation_offset = 0
        hdri_path = os.path.join(addon_dir, "assets", "hdri", hdri_file)
        if not os.path.isfile(hdri_path):
            self.report({'ERROR'}, f"HDRI file not found at path: {hdri_path}")
            return {'CANCELLED'}
        setup_world_nodes(hdri_path, mapping_rotation_deg=final_mapping_deg)
        self.report({'INFO'}, f"HDRI applied: {hdri_file}")
        return {'FINISHED'}

# Save Preset Operator

class HDRI_OT_SavePreset(Operator):
    bl_idname = "hdri.save_preset"
    bl_label = ""
    bl_description = "Save the current custom HDRI as a new preset"

    preset_name: StringProperty(name="Name", default="")  # type: ignore

    def invoke(self, context, event):
        props = context.scene.hdri_props
        file_name = os.path.basename(props.custom_hdri_filepath) if props.custom_hdri_filepath else ""
        self.bl_label = f"Save {file_name} as Preset"
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "preset_name", text="Name")

    def execute(self, context):
        props = context.scene.hdri_props
        if props.hdri_preset != "CUSTOM":
            self.report({'ERROR'}, "Only custom HDRI can be saved as a preset.")
            return {'CANCELLED'}
        if not props.custom_hdri_filepath or not os.path.isfile(props.custom_hdri_filepath):
            self.report({'ERROR'}, "No valid custom HDRI file specified.")
            return {'CANCELLED'}
        if not self.preset_name.strip():
            self.report({'ERROR'}, "Name cannot be empty.")
            return {'CANCELLED'}

        addon_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
        assets_dir = os.path.join(addon_dir, "assets", "hdri")
        if not os.path.isdir(assets_dir):
            os.makedirs(assets_dir)
        src_path = props.custom_hdri_filepath
        dest_file = os.path.basename(src_path)
        dest_path = os.path.join(assets_dir, dest_file)
        try:
            shutil.copy2(src_path, dest_path)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to copy HDRI file: {e}")
            return {'CANCELLED'}

        json_path = os.path.join(addon_dir, "properties", "hdri.json")
        try:
            if os.path.isfile(json_path):
                with open(json_path, 'r') as f:
                    data = json.load(f)
            else:
                data = []
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load JSON: {e}")
            return {'CANCELLED'}

        new_entry = {"file": dest_file, "display_name": self.preset_name}
        data.append(new_entry)
        try:
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to save JSON: {e}")
            return {'CANCELLED'}

        presets = load_hdri_presets()
        valid_values = [entry.get("file", "Unknown") for entry in presets]
        valid_values.append("CUSTOM")
        if dest_file in valid_values:
            context.scene.hdri_props.hdri_preset = dest_file
        else:
            context.scene.hdri_props.hdri_preset = "CUSTOM"

        self.report({'INFO'}, f"Preset saved: {self.preset_name}")
        return {'FINISHED'}

# Panel

class HDRI_PT_Panel(Panel):
    bl_label = "Quick HDRI"
    bl_idname = "HDRI_PT_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "world"

    def draw(self, context):
        layout = self.layout
        props = context.scene.hdri_props
        layout.prop(props, "hdri_preset")
        if props.hdri_preset == "CUSTOM":
            row = layout.row(align=True)
            row.prop(props, "custom_hdri_filepath")
            row.operator("hdri.save_preset", text="", icon="FILE_TICK")
        world = context.scene.world
        mapping_found = False
        if world and world.use_nodes:
            for node in world.node_tree.nodes:
                if node.type == 'MAPPING':
                    mapping_found = True
                    break
        if mapping_found:
            layout.prop(props, "hdri_rotation_offset")
        layout.operator("hdri.apply", text="Apply HDRI")

# Properties

def load_hdri_presets():
    json_path = os.path.join(os.path.dirname(__file__), "..", "properties", "hdri.json")
    presets = refresh_json_asset(json_path)
    return presets if presets is not None else []

def hdri_preset_items(self, context):
    presets = load_hdri_presets()
    items = []
    if isinstance(presets, list):
        for entry in presets:
            file_name = entry.get("file", "Unknown")
            display_name = entry.get("display_name", file_name)
            items.append((file_name, display_name, f"HDRI: {display_name}"))
    items.sort(key=lambda x: x[1].lower())  # sort alphabetically by display_name
    items.append(("CUSTOM", "Custom", "Load a custom HDRI file"))
    return items

def update_hdri_rotation_offset(self, context):
    world = context.scene.world
    if world and world.use_nodes:
        for node in world.node_tree.nodes:
            if node.type == 'MAPPING':
                node.inputs["Rotation"].default_value[2] = math.radians(self.hdri_base_rotation + self.hdri_rotation_offset)

class HDRIProperties(PropertyGroup):
    hdri_preset: EnumProperty(
        name="",
        description="Select an HDRI preset",
        items=hdri_preset_items
    )  # type: ignore
    hdri_base_rotation: FloatProperty(
        name="HDRI Base Rotation",
        description="Computed base rotation (degrees)",
        default=0,
        options={'HIDDEN'}
    )  # type: ignore
    hdri_rotation_offset: FloatProperty(
        name="Rotation",
        description="User-defined offset added to the computed HDRI rotation (degrees)",
        default=0,
        min=-360,
        max=360,
        update=update_hdri_rotation_offset
    )  # type: ignore
    custom_hdri_filepath: StringProperty(
        name="",
        description="File path to a custom HDRI",
        subtype='FILE_PATH',
        default=""
    )  # type: ignore

# Register

classes = [HDRI_OT_Apply, HDRI_OT_SavePreset, HDRI_PT_Panel, HDRIProperties]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.hdri_props = PointerProperty(type=HDRIProperties)

def unregister():
    del bpy.types.Scene.hdri_props
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()