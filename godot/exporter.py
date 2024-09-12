import shutil
import subprocess
from bpy.types import Context
from ..common import * 
from ..preferences import * 
from .. import Layer, Mask
from bpy.props import *
from bpy.types import PropertyGroup, Panel, Operator, UIList, Scene

import bpy

# export shader, choose location, save file
class ExportShader(Operator):
    """Export to godot shader"""

    bl_label = "Export Shader"
    bl_idname = "godot.export"

    filepath: StringProperty(subtype='FILE_PATH', options={'SKIP_SAVE'})

    use_shortcut = False
    shader_generation_test = False

    godot_directory = "/home/bocilmania/Documents/projects/godot/witch/"

    script_template = '''
shader_type spatial;

uniform int heightmap_min_layers : hint_range(1, 64) = 32;
uniform int heightmap_max_layers : hint_range(1, 64) = 32;
{0}vec4 layer(vec4 foreground, vec4 background) {{
    return foreground * foreground.a + background * (1.0 - foreground.a);
}}

vec2 setHeight(vec2 uv, vec3 view_dir, sampler2D heightmap, float scale){{
	vec2 base_uv = uv;

	// Height Deep Parallax: Enabled
	float num_layers = mix(float(heightmap_max_layers), float(heightmap_min_layers), abs(dot(vec3(0.0, 0.0, 1.0), view_dir)));
	float layer_depth = 1.0 / num_layers;
	float current_layer_depth = 0.0;
	vec2 p = view_dir.xy * scale * 0.01;
	vec2 delta = p / num_layers;
	vec2 ofs = base_uv;
	float depth = 1.0 - texture(heightmap, ofs).r;

	float current_depth = 0.0;
	while (current_depth < depth) {{
		ofs -= delta;
		depth = 1.0 - texture(heightmap, ofs).r;

		current_depth += layer_depth;
	}}

	vec2 prev_ofs = ofs + delta;
	float after_depth = depth - current_depth;
	float before_depth = (1.0 - texture(heightmap, prev_ofs).r) - current_depth + layer_depth;

	float weight = after_depth / (after_depth - before_depth);
	ofs = mix(ofs, prev_ofs, weight);
	base_uv = ofs;

	return base_uv;
}}

void fragment() {{ 
    vec3 view_dir = normalize(normalize(-VERTEX + EYE_OFFSET) * mat3(TANGENT, -BINORMAL, NORMAL));{1}
    ALBEDO = albedo_all.rgb;
}}

'''

    script_vars = '''
uniform sampler2D {0}:source_color, filter_linear_mipmap, repeat_enable;
uniform vec2 {1} = vec2({2},{3}); 
'''
    script_vars_roughness = "uniform sampler2D {}_roughness:hint_roughness_r, filter_linear_mipmap, repeat_enable;\n"

    script_vars_normal = '''uniform sampler2D {0}_normal:hint_roughness_normal, filter_linear_mipmap, repeat_enable;
uniform float {0}_normal_depth = 1.0;
'''

    script_vars_heightmap = "uniform sampler2D {0}_heightmap:hint_default_black, filter_linear_mipmap, repeat_enable;\nuniform float {0}_heightmap_scale = 5.0;\n"

    script_mask_vars = "uniform sampler2D {0};"
    
    script_fragment_base_uv_heightmap = '''
    scaled_uv_{0} = setHeight(scaled_uv_{0}, view_dir, {1}_heightmap, {1}_heightmap_scale);'''

    script_fragment_var = '''

    vec2 scaled_uv_{0} = UV * {1};{3}
    vec4 albedo_{0} = texture({2}, scaled_uv_{0});'''

    script_fragment_roughness_var = '''
    vec4 roughness_{0} = texture({1}, scaled_uv_{0});'''
    script_fragment_normal_var = '''
    vec4 normal_{0} = texture({1}, scaled_uv_{0});
    vec4 normal_depth_{0} = vec4({1}_depth, 0, 0, 1);'''

    script_mask_fragment_var = '''
    vec4 mask_{0} = texture({1}, scaled_uv_{0});
    albedo_{0}.a = mask_{0}.r;''' 
    script_mask_normal_var = '''
    normal_{0}.a = mask_{0}.r;
    normal_depth_{0}.a = mask_{0}.r;'''
    script_mask_roughness_var = '''
    roughness_{0}.a = mask_{0}.r;'''


    script_albedo_combine_0 = '''

    vec4 albedo_all = layer(albedo_0, albedo_1);'''

    script_albedo_combine_next = '''
    albedo_all = layer(albedo_all, albedo_{0});
'''

    script_roughness_1 = '''
    vec4 roughness_all = roughness_{};
'''
    script_roughness_combine_0 = '''
    vec4 roughness_all = layer(roughness_{0}, roughness_{1});'''

    script_roughness_combine_next = '''
    roughness_all = layer(roughness_all, roughness_{0});
'''
    script_roughness_fragment = '''
    vec4 roughness_texture_channel = vec4(0.33, 0.33, 0.33, 0.0);
    float rough = dot(roughness_all, roughness_texture_channel);

    ROUGHNESS = rough;
'''

    script_normal_1 = '''
    vec4 normal_all = normal_{0};
    vec4 normal_depth_all = normal_depth_{0};
'''
    script_normal_combine_0 = '''
    vec4 normal_all = layer(normal_{0}, normal_{1});
    vec4 normal_depth_all = layer(normal_depth_{0}, normal_depth_{1});'''

    script_normal_combine_next = '''
    normal_all = layer(normal_all, normal_{0});
    normal_depth_all = layer(normal_depth_all, normal_depth_{0});'''

    script_normal_fragment = '''
    NORMAL_MAP = normal_all.rgb;
    NORMAL_MAP_DEPTH = normal_depth_all.r;
'''
  #vec4 albedo = texture({1}, scaled_uv_{0});

    def get_godot_directory(self, path:str):

        current_dir = os.path.dirname(path)
        godot_project_dir = ""

        while godot_project_dir == "":
            for filename in os.listdir(current_dir):
                fl = os.path.join(current_dir, filename)
                if os.path.isfile(fl):
                    if filename == "project.godot":
                        godot_project_dir = current_dir
                        break
                    # print("check ", filename, " = ", fl)
            # move up directory

            parent_dir = os.path.dirname(current_dir)
            if parent_dir == current_dir:
                # print("break here ", current_dir)
                break
            current_dir = parent_dir
        print("godot project ", godot_project_dir)

        return godot_project_dir
    
    def fix_filename(self, filename:str):
        base, ext = os.path.splitext(filename)
        retval = filename

        if ext != ".gdshader":
            retval = base + ".gdshader"
        else:
            print("File extension is already .gdshader")

        print(f"File extension changed to: {retval}")
        return retval

    def execute(self, context):
        node = get_active_ypaint_node()
        yp = node.node_tree.yp

        print("====================================")
        index = 0
        layer:Layer.YLayer

        global_vars = ""
        fragment_vars = ""
        combine_content = ""

        # get directory of filepath
        my_directory = "/home/bocilmania/Documents/projects/godot/witch/models/box"
        # addon directory
        addon_dir = os.path.dirname(os.path.realpath(__file__))

        if self.use_shortcut:
            self.filepath = os.path.join(my_directory, "box.gdshader")
        else:
            my_directory = os.path.dirname(self.filepath)

        if not os.path.exists(my_directory):
            print("create directory ", my_directory)
            os.makedirs(my_directory)
        else:
            print("directory exist ", my_directory)

        self.godot_directory = self.get_godot_directory(self.filepath)

        if self.godot_directory == "":
            self.report({'ERROR'}, "This is not a godot directory")
            return {'CANCELLED'}

        self.filepath = self.fix_filename(self.filepath)

        print("save to ", self.filepath, " in ", self.godot_directory)

        base_arg = ["godot", "--headless", "--path", self.godot_directory]
        asset_args = []

        relative_path = os.path.relpath(self.filepath, self.godot_directory)
        relative_path = os.path.dirname(relative_path)
        
        print(f"Relative path: {relative_path}")


        roughness_overrides = []
        normal_overrides = []
        
        for layer_idx, layer in enumerate(yp.layers):
            if layer.enable:
                mapping = get_layer_mapping(layer)

                layer_var = "layer_"+str(index)

                scale_var = layer_var + "_scale"

                skala = mapping.inputs[3].default_value
                global_vars += self.script_vars.format(layer_var, scale_var, skala.x, skala.y)

                heightmap_uv_script = ""
                fragment_var = ""

                source = get_layer_source(layer)

                image_path = source.image.filepath_from_user()

                asset_args.append(layer_var)
                asset_args.append(bpy.path.basename(image_path))

                # copy to directory 
                print("copy ", image_path, " to ", my_directory)
                shutil.copy(image_path, my_directory)

                yp = layer.id_data.yp

                channel:Layer.YLayerChannel
                for id_ch, channel in enumerate(layer.channels):
                    ch_name = yp.channels[id_ch].name
                    if channel.enable:
                        print("channel ", channel.name, " name_", yp.channels[id_ch].name)
                        ch_image_path = ""
                        ch_image_path_1 = ""

                        if channel.override:
                            source_ch = get_channel_source(channel, layer)
                            ch_image_path = source_ch.image.filepath_from_user()
                    
                            print("channel path 0", id_ch, " = ",ch_image_path)

                        if channel.override_1:
                            source_ch_1 = get_channel_source_1(channel, layer)
                            ch_image_path_1 = source_ch_1.image.filepath_from_user()
                           
                            print("channel path 1", id_ch, " = ",ch_image_path_1)

                        if ch_image_path != "":
                            shutil.copy(ch_image_path, my_directory)
                        if ch_image_path_1 != "":
                            shutil.copy(ch_image_path_1, my_directory)

                        if ch_name == "Roughness":
                            global_vars += self.script_vars_roughness.format(layer_var)
                            roughness_overrides.append(layer_idx)

                            layer_roughness = layer_var + "_roughness"
                            asset_args.append(layer_roughness)
                            asset_args.append(bpy.path.basename(ch_image_path))
                            fragment_var += self.script_fragment_roughness_var.format(index, layer_roughness)
                            
                        elif ch_name == "Normal":
                            global_vars += self.script_vars_normal.format(layer_var)
                            global_vars += self.script_vars_heightmap.format(layer_var)
                            normal_overrides.append(layer_idx)

                            layer_heightmap = layer_var + "_heightmap"

                            heightmap_uv_script = self.script_fragment_base_uv_heightmap.format(index, layer_var)
                            asset_args.append(layer_heightmap)
                            asset_args.append(bpy.path.basename(ch_image_path)) # todo : override 0 or override 1

                            layer_normal = layer_var + "_normal"
                            asset_args.append(layer_normal)
                            asset_args.append(bpy.path.basename(ch_image_path_1)) # todo : override 0 or override 1
                            fragment_var += self.script_fragment_normal_var.format(index, layer_normal)
                
                fragment_var = self.script_fragment_var.format(index, scale_var, layer_var, heightmap_uv_script) + fragment_var
                fragment_vars += fragment_var

                # print("filepath ", index, " = ",source.image.filepath_from_user())
                # print("rawpath ", index, " = ",source.image.filepath)
                # print("path user ", index, " = ",source.image.filepath_raw)
                msk:Mask.YLayerMask
                for idx, msk in enumerate(layer.masks):
                    mask_var = layer_var + "_mask_" + str(idx)
                    global_vars += self.script_mask_vars.format(mask_var)
                    fragment_vars += self.script_mask_fragment_var.format(index, mask_var)

                    if layer_idx in roughness_overrides:
                        fragment_vars += self.script_mask_roughness_var.format(index)
                    if layer_idx in normal_overrides:
                        fragment_vars += self.script_mask_normal_var.format(index)


                    mask_tree = get_mask_tree(msk)
                    mask_source = mask_tree.nodes.get(msk.source)

                    mask_image_path = mask_source.image.filepath_from_user()

                    if mask_image_path == "":
                        print("unpack item ", msk.name)
                        bpy.ops.file.unpack_item(id_name=msk.name, method='WRITE_ORIGINAL')
                        mask_image_path = mask_source.image.filepath_from_user()
                    else:
                        print("mask path exist ", mask_image_path)

                    asset_args.append(mask_var)
                    asset_args.append(bpy.path.basename(mask_image_path))

                    shutil.copy(mask_image_path, my_directory)
                    print("copy ", mask_image_path, " to ", my_directory)
                global_vars += "\n"

                if index == 1:
                    combine_content += self.script_albedo_combine_0
                elif index > 1:
                    combine_content += self.script_albedo_combine_next.format(index)
                    
                index += 1

        if len(roughness_overrides) > 0:
            if len(roughness_overrides) == 1:
                combine_content += self.script_roughness_1.format(roughness_overrides[0])
            else:
                for lyr_idx, lyr in enumerate(roughness_overrides):
                    if lyr_idx == 1:
                        combine_content += self.script_roughness_combine_0.format(roughness_overrides[lyr_idx - 1], roughness_overrides[lyr_idx])
                    elif lyr_idx > 1:
                        combine_content += self.script_roughness_combine_next.format(lyr)

            combine_content += self.script_roughness_fragment

        if len(normal_overrides) > 0:
            if len(normal_overrides) == 1:
                combine_content += self.script_normal_1.format(normal_overrides[0])
            else:
                for lyr_idx, lyr in enumerate(normal_overrides):
                    if lyr_idx == 1:
                        combine_content += self.script_normal_combine_0.format(normal_overrides[lyr_idx - 1], normal_overrides[lyr_idx])
                    elif lyr_idx > 1:
                        combine_content += self.script_normal_combine_next.format(lyr)

            combine_content += self.script_normal_fragment
        
        print("parameter ", asset_args)
        fragment_vars += combine_content

        content_shader = self.script_template.format(global_vars, fragment_vars)

        print(content_shader)

        script_location = os.path.join(addon_dir, "blender_import.gd")
        print("addon dir ", script_location)

        name_asset = bpy.path.display_name_from_filepath(self.filepath)

        print("file name", name_asset)

        if not self.shader_generation_test:
            file = open(self.filepath, "w")
            file.write(content_shader)
            file.close()

            all_params = base_arg + ["-s", script_location, "--", name_asset, relative_path] + asset_args
            print("all params=", " ".join(all_params))
            print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
            print(subprocess.run(base_arg + ["--import"], capture_output=True))
            print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
            print(subprocess.run(all_params, capture_output=True))
            print(subprocess.run(base_arg + ["--import"], capture_output=True))

        return {'FINISHED'}

    def invoke(self, context, event):
        if self.use_shortcut:
            return self.execute(context)
        else:
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}
    

classes = [ExportShader]

def register():
    for cl in classes:
        bpy.utils.register_class(cl)


def unregister():
    for cl in classes:
        bpy.utils.unregister_class(cl)
    

if __name__ == "__main__":
    register()