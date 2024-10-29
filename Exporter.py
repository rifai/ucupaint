from bpy.types import Operator
import shutil

import bpy, json
from .common import *
from .Layer import *

import mathutils


class YExporter(Operator):

	bl_idname = "node.y_export"
	bl_label = "Export Ucupaint"
	version = (0, 1, 0)

	filetype = ".ucon"
	filetype_packed = ".ucu"
	filepath: StringProperty(subtype='FILE_PATH', options={'SKIP_SAVE'})
	export_gltf: BoolProperty(name="Export GLTF", default=False)

	blender_to_godot = mathutils.Matrix((
							(1, 0, 0, 0),
							(0, 0, 1, 0),
							(0, -1, 0, 0),
							(0, 0, 0, 1)
						))

	def fix_filename(self, filename:str):
		base, ext = os.path.splitext(filename)
		retval = filename

		if ext != self.filetype:
			retval = base + self.filetype
		else:
			print(f"File extension is already {self.filetype}")

		print(f"File extension changed to: {retval}")

		return retval
	
	def execute(self, context):
		node = get_active_ypaint_node()
		yp = node.node_tree.yp

		print("====================================")
		index = 0
		layer:YLayer

		self.filepath = self.fix_filename(self.filepath)

		my_directory = os.path.dirname(self.filepath)

		if not os.path.exists(my_directory):
			print("create directory ", my_directory)
			os.makedirs(my_directory)
		else:
			print("directory exist ", my_directory)

		print(f"Relative path: {self.filepath}")
		# Prepare data to be saved
		data = {
			"version": self.version,
			"layers": []
		}


		albedo_overrides = []
		roughness_overrides = []
		normal_overrides = []
		bump_overrides = []

		copying_files = []

		tmpscene = bpy.data.scenes.new('Temp Scene')
		settings = tmpscene.render.image_settings
		print("file format ", settings.file_format)

		for layer_idx, layer in enumerate(yp.layers):
			if layer.enable:
				intensity_layer = get_entity_prop_value(layer, 'intensity_value')

				layer_data = {
                    "index": index,
                    "name": layer.name,
					"intensity_value": intensity_layer
                }

				source = get_layer_source(layer)

				if layer.type == "IMAGE":
					texcoord_type = layer.texcoord_type
					layer_var = "layer_"+str(index)
					image_path = source.image.filepath_from_user()

					if texcoord_type == "UV":
						layer_data["decal"] = False
						
						albedo = {
							"key"	: layer_var,
							"value" : bpy.path.basename(image_path)
						}
						copying_files.append(image_path)

						layer_data["albedo"] = albedo

						for id_ch, channel in enumerate(layer.channels):
							ch_name = yp.channels[id_ch].name
							if channel.enable:
								ch_image_path = ""
								ch_image_path_1 = ""

								intensity_channel = get_entity_prop_value(channel, 'intensity_value')

								print("inter channel ", ch_name, " intensity ", intensity_channel)

								if channel.override:
									source_ch = get_channel_source(channel, layer)
									ch_image_path = source_ch.image.filepath_from_user()
							
									print("channel path 0", id_ch, " = ",ch_image_path)

								if channel.override_1:
									source_ch_1 = get_channel_source_1(channel, layer)
									ch_image_path_1 = source_ch_1.image.filepath_from_user()
								
									print("channel path 1", id_ch, " = ",ch_image_path_1)

								if ch_image_path != "":
									# if "exr" in ch_image_path:
									#     png_path = os.path.join(my_directory, bpy.path.display_name_from_filepath(ch_image_path) + ".png")
									#     self.convert_exr_to_png(source_ch.image, png_path)
									#     ch_image_path = png_path
									# shutil.copy(ch_image_path, my_directory)
									copying_files.append(ch_image_path)

								if ch_image_path_1 != "":
									# shutil.copy(ch_image_path_1, my_directory)
									copying_files.append(ch_image_path_1)

								if ch_name == "Color":
									albedo["intensity_value"] = intensity_channel
								elif ch_name == "Roughness":
									roughness = {
										"key"	: layer_var + "_roughness",
										"value" : bpy.path.basename(ch_image_path),
										"intensity_value": intensity_channel
									}
									layer_data["roughness"] = roughness

								elif ch_name == "Normal":
									if ch_image_path != "":
										heightmap = {
											"key"	: layer_var + "_heightmap",
											"value" : bpy.path.basename(ch_image_path),
											"intensity_value": intensity_channel
										}
										layer_data["heightmap"] = heightmap

									if ch_image_path_1 != "":
										layer_normal = layer_var + "_normal"
										
										normal = {
											"key"	: layer_normal,
											"value" : bpy.path.basename(ch_image_path_1),
											"intensity_value": intensity_channel
										}
										layer_data["normal"] = normal
										
						msk:Mask.YLayerMask
						for idx, msk in enumerate(layer.masks):
							mask_type = msk.type
							print("mask type ", mask_type)
							mask_data = {
								"type"	: mask_type,
							}

							intensity_mask = get_entity_prop_value(msk, 'intensity_value')


							if mask_type == "IMAGE":
								mask_var = layer_var + "_mask_" + str(idx)

								mask_tree = get_mask_tree(msk)
								mask_source = mask_tree.nodes.get(msk.source)

								mask_image_path = mask_source.image.filepath_from_user()

								if mask_image_path == "":
									# todo : copy or save as

									format_ext = "."+settings.file_format.lower()
									filepath_new = os.path.join(my_directory, msk.name) + format_ext
									print("unpack item ", msk.name, " to ", filepath_new)

									mask_image = bpy.data.images[msk.name]
									override = bpy.context.copy()
									override['edit_image'] = mask_image
									if is_bl_newer_than(4):
										with bpy.context.temp_override(**override):
											bpy.ops.image.save_as(filepath=filepath_new, copy=True, )
									else: bpy.ops.image.save_as(override, filepath=filepath_new)

									# remove_datablock(bpy.data.images, new_image)
									print("mask packed1", mask_source.name)
									print("mask packed2", msk.name)

									mask_image_path = filepath_new
								else:
									print("mask path exist ", mask_image_path)
									copying_files.append(mask_image_path)

								mask_data["key"] = mask_var
								mask_data["value"] = bpy.path.basename(mask_image_path)

							elif mask_type == "COLOR_ID":
								colorid_col = get_mask_color_id_color(msk)
								mask_data["color"] = [colorid_col[0], colorid_col[1], colorid_col[2]]
								mask_data["index"] = colorid_col
							
							mask_data["intensity_value"] = intensity_mask
							layer_data["mask"] = mask_data
							# if layer_idx in roughness_overrides:
							# 	fragment_vars += self.script_mask_roughness_var.format(index)
							# if layer_idx in normal_overrides:
							# 	fragment_vars += self.script_mask_normal_var.format(index)

						index += 1
					elif texcoord_type == "Decal":
						layer_tree = get_tree(layer)
						texcoord = layer_tree.nodes.get(layer.texcoord)
						decal_obj = texcoord.object
						local_matrix = decal_obj.matrix_local

						image = None
						if source:
							image = source.image

						if image:
							if image.size[0] > image.size[1]:
								decal_scale = (image.size[1] / image.size[0], 1.0, 1.0)
							else: 
								decal_scale = (1.0, image.size[0] / image.size[1], 1.0)

						local_matrix = self.blender_to_godot @ local_matrix# @ blender_to_godot.inverted()
						# print("local_matrix  3", local_matrix)
						local_matrix.transpose()

						# affine inverse
						local_matrix = local_matrix.inverted()

						inp = get_entity_prop_input(layer, "decal_distance_value")
	
						new_path = resize_decal_texture(my_directory, image)

						layer_data["decal"] = True
						layer_data["key"] = layer_var
						layer_data["value"] = bpy.path.basename(image_path)
						layer_data["decal_distance_value"] = inp.default_value
						layer_data["decal_scale"] = [decal_scale[0], decal_scale[1], decal_scale[2]]
						layer_data["decal_matrix"] = [
							local_matrix[0][0], local_matrix[0][1], local_matrix[0][2], local_matrix[0][3], 
							local_matrix[1][0], local_matrix[1][1], local_matrix[1][2], local_matrix[1][3], 
							local_matrix[2][0], local_matrix[2][1], local_matrix[2][2], local_matrix[2][3], 
							local_matrix[3][0], local_matrix[3][1], local_matrix[3][2], local_matrix[3][3],
						]

						index += 1

				data["layers"].append(layer_data)
		

		data["copying_files"] = copying_files
		# Save data to JSON file
		with open(self.filepath, 'w') as json_file:
			json.dump(data, json_file, indent=4)

		if self.export_gltf:
			name_asset = bpy.path.display_name_from_filepath(self.filepath)

			bpy.ops.export_scene.gltf(export_format='GLTF_SEPARATE', export_apply=True, filepath=os.path.join(my_directory, name_asset + ".glb"), 
									export_vertex_color="ACTIVE", export_tangents=True, use_selection=True, export_texture_dir="gltf_textures")
		# copying all textures
		for file in copying_files:
			shutil.copy(file, my_directory)
		return {'FINISHED'}

	def invoke(self, context, event):
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
		
	def draw(self, context):
		col = self.layout.column()
		col.prop(self, "export_gltf")


def resize_decal_texture(directory_path, image, padding = 1) -> str:
	scaled_image = image.copy()

	new_width = 2 ** math.ceil(math.log2(image.size[0])) - padding * 2
	new_height = 2 ** math.ceil(math.log2(image.size[1])) - padding * 2

	print("scale from ", image.size[0], image.size[1], " to ", new_width, new_height)

	scaled_image.scale(new_width, new_height)

	new_width = new_width + 2 * padding
	new_height = new_height + 2 * padding
	
	new_image = bpy.data.images.new("temp-image", width=new_width, height=new_height, alpha=True)

	# Copy image pixels
	# copy_image_pixels(image, new_image)

	target_pxs = numpy.empty(shape=new_height*new_width*4, dtype=numpy.float32)
	source_pxs = numpy.empty(shape=scaled_image.size[0]*scaled_image.size[1]*4, dtype=numpy.float32)
	new_image.pixels.foreach_get(target_pxs)
	scaled_image.pixels.foreach_get(source_pxs)

	# Set array to 3d
	target_pxs.shape = (new_height, new_width, 4)
	source_pxs.shape = (scaled_image.size[1], scaled_image.size[0], 4)

	target_pxs[padding:padding+scaled_image.size[1], padding:padding+scaled_image.size[0]] = source_pxs
	target_pxs[:padding, :] = [0, 0, 0, 0]  # Top border
	target_pxs[-padding:, :] = [0, 0, 0, 0]  # Bottom border
	target_pxs[:, :padding] = [0, 0, 0, 0]  # Left border
	target_pxs[:, -padding:] = [0, 0, 0, 0]  # Right border

	new_image.pixels.foreach_set(target_pxs.ravel())

	# extract file name and extension
	base, ext = os.path.splitext(image.filepath_from_user())
	filename = bpy.path.display_name_from_filepath(image.filepath_from_user())
	filepath_new = os.path.join(directory_path, filename) + ext

	print("save as decal", filepath_new)

	override = bpy.context.copy()
	override['edit_image'] = new_image
	if is_bl_newer_than(4):
		with bpy.context.temp_override(**override):
			bpy.ops.image.save_as(filepath=filepath_new)
	else: bpy.ops.image.save_as(override, filepath=filepath_new)

	remove_datablock(bpy.data.images, new_image)
	remove_datablock(bpy.data.images, scaled_image)

	return filepath_new


classes = [YExporter]

def register():
	for cl in classes:
		bpy.utils.register_class(cl)


def unregister():
	for cl in classes:
		bpy.utils.unregister_class(cl)
	

if __name__ == "__main__":
	register()