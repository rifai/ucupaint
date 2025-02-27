from bpy.types import Operator
import shutil

import bpy, json
from .common import *
from .Layer import *

import mathutils

blender_to_godot = mathutils.Matrix((
							(1, 0, 0, 0),
							(0, 0, 1, 0),
							(0, -1, 0, 0),
							(0, 0, 0, 1)
						))
version = (0, 1, 0)

filetype = ".ucon"
filetype_packed = ".ucu"

class YSceneExporter(Operator):
	bl_idname = "node.y_scene_export"
	bl_label = "Export Ucupaint"

	filepath: StringProperty(subtype='FILE_PATH', options={'SKIP_SAVE'})

	def invoke(self, context, event):
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
		
	def execute(self, context):
		print("file path ", self.filepath)
		my_directory = os.path.dirname(self.filepath)

		# print all objects in the scene
		for obj in bpy.context.scene.objects:
			node = get_active_ypaint_node(obj)
			if node != None:
				file_path = os.path.join(my_directory, obj.name, obj.name + filetype)
				# file_path = fix_filename(file_path)

				print("node ", obj.name, "=", file_path)
				# export per object
				generate_ucupaint_data(node, file_path, False)


		return {'FINISHED'}
	

class YExporter(Operator):

	bl_idname = "node.y_export"
	bl_label = "Export Ucupaint"

	filepath: StringProperty(subtype='FILE_PATH', options={'SKIP_SAVE'})
	export_gltf: BoolProperty(name="Export Mesh", default=False)
	pack_file: BoolProperty(name="Pack File", default=False)	
	
	def execute(self, context):
		node = get_active_ypaint_node()
		file_path = fix_filename(self.filepath)
		pack_file = self.pack_file

		generate_ucupaint_data(node, file_path, pack_file)

		return {'FINISHED'}

	def invoke(self, context, event):
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
		
	def draw(self, context):
		col = self.layout.column()
		col.prop(self, "pack_file")


def fix_filename(filename:str):
	base, ext = os.path.splitext(filename)
	retval = filename

	if ext != filetype:
		retval = base + filetype
	else:
		print(f"File extension is already {filetype}")

	print(f"File extension changed to: {retval}")

	return retval

def generate_ucupaint_data(node, file_path, pack_file):
	print("====================================")
	yp = node.node_tree.yp
	inputs = node.inputs

	index = 0
	layer:YLayer

	my_directory = os.path.dirname(file_path)

	if not os.path.exists(my_directory):
		print("create directory ", my_directory)
		os.makedirs(my_directory)
	else:
		print("directory exist ", my_directory)

	print(f"Relative path: {file_path}")
	# Prepare data to be saved
	data = {
		"version": version,
		"layers": [],
	}

	for i in inputs:
		print("input ", i.name, " = ", i.default_value, " type ", i.type)
		in_key = i.name.lower()

		if i.type == 'VALUE':
			data[in_key] = i.default_value
		else:
			data[in_key] = i.default_value[:]

	copying_files = []

	tmpscene = bpy.data.scenes.new('Temp Scene')
	settings = tmpscene.render.image_settings
	print("file format ", settings.file_format)
	format_ext = "."+settings.file_format.lower()

	# Remove temporary scene
	bpy.data.scenes.remove(tmpscene)

	flat_layers = []

	for layer_idx, layer in enumerate(yp.layers):
		if layer.enable:
			print("layer=", layer.type, " name=", layer.name, "parent index=", layer.parent_idx)
			intensity_layer = get_entity_prop_value(layer, 'intensity_value')

			layer_data = {
				"intensity_value": intensity_layer,
				"masks": [],
				"id": layer_idx,
				"name": layer.name,
			}

			mods = get_modifiers(layer.modifiers)
			layer_data["modifiers"] = mods

			source = get_layer_source(layer)
			channels_data = {}

			if layer.type == "IMAGE":
				texcoord_type = layer.texcoord_type
				image_path = source.image.filepath_from_user()
				layer_data["type"] = layer.texcoord_type

				if texcoord_type == "UV":
					mapping = get_layer_mapping(layer)
					use_uniform_scale = layer.enable_uniform_scale

					if use_uniform_scale:
						uniform_scale = get_entity_prop_value(layer, 'uniform_scale_value')
						layer_data["scale"] = [uniform_scale, uniform_scale, uniform_scale]
					else:
						skala = mapping.inputs[3].default_value
						layer_data["scale"] = [skala.x, skala.y, skala.z]

					offset = mapping.inputs[1].default_value
					layer_data["offset"] = offset[:]
					rot = mapping.inputs[2].default_value
					layer_data["rotation"] = rot[:]

					print("copying image_path", image_path)
					if image_path == "":
						image_path = copy_unpack_image(layer.name, my_directory, format_ext)
					else:
						copying_files.append(image_path)
					
					layer_data["source"] = bpy.path.basename(image_path)

				elif texcoord_type == "Decal":
					layer_tree = get_tree(layer)
					texcoord = layer_tree.nodes.get(layer.texcoord)
					decal_obj = texcoord.object
					original_matrix = decal_obj.matrix_local
					godot_matrix = decal_obj.matrix_local

					image = None
					if source:
						image = source.image

					if image:
						if image.size[0] > image.size[1]:
							decal_scale = (image.size[1] / image.size[0], 1.0, 1.0)
						else: 
							decal_scale = (1.0, image.size[0] / image.size[1], 1.0)
					
					# todo : matrix for other engines
					godot_matrix = blender_to_godot @ godot_matrix# @ blender_to_godot.inverted()
					# print("local_matrix  3", local_matrix)
					godot_matrix.transpose()

					# affine inverse
					godot_matrix = godot_matrix.inverted()

					inp = get_entity_prop_input(layer, "decal_distance_value")

					resize_decal_texture(my_directory, image)

					layer_data["source"] = bpy.path.basename(image_path)
					layer_data["scale"] = [decal_scale[0], decal_scale[1], decal_scale[2]]

					decal_attributes = {
						"distance" : inp.default_value,
						"matrix" : [
							original_matrix[0][0], original_matrix[0][1], original_matrix[0][2], original_matrix[0][3], 
							original_matrix[1][0], original_matrix[1][1], original_matrix[1][2], original_matrix[1][3], 
							original_matrix[2][0], original_matrix[2][1], original_matrix[2][2], original_matrix[2][3], 
							original_matrix[3][0], original_matrix[3][1], original_matrix[3][2], original_matrix[3][3],
						],
						"matrix_godot" :  [
							godot_matrix[0][0], godot_matrix[0][1], godot_matrix[0][2], godot_matrix[0][3], 
							godot_matrix[1][0], godot_matrix[1][1], godot_matrix[1][2], godot_matrix[1][3], 
							godot_matrix[2][0], godot_matrix[2][1], godot_matrix[2][2], godot_matrix[2][3], 
							godot_matrix[3][0], godot_matrix[3][1], godot_matrix[3][2], godot_matrix[3][3],
						]
					}
					layer_data["decal"] = decal_attributes

			elif layer.type == "COLOR":
				layer_data["type"] = "COLOR"
				color_layer = source.outputs[0].default_value
				layer_data["color"] = color_layer[:]

			elif layer.type == "GROUP":
				layer_data["type"] = "GROUP"
				layer_data["layers"] = []

				print("add group layer ", layer.name)


			for id_ch, channel in enumerate(layer.channels):
				ch_name = yp.channels[id_ch].name
				if channel.enable:
					ch_image_path = ""
					ch_image_path_1 = ""

					intensity_channel = get_entity_prop_value(channel, 'intensity_value')

					print("inter channel ", ch_name, " intensity ", intensity_channel)
					key_name = ch_name.lower()

					channel_info = {
						"intensity_value" : intensity_channel,
						"blend" : channel.blend_type,
					}

					chan_mods = get_modifiers(channel.modifiers)
					channel_info["modifiers"] = chan_mods

					is_normal = ch_name == "Normal"
					normal_type = channel.normal_map_type.lower()
					if layer.type == "GROUP" and is_normal:
						print("normal type of group=", normal_type)
						print("overrides=", channel.override, channel.override_1)

					is_normal_map = is_normal and "normal" in normal_type
					is_bump_map = is_normal and "bump" in normal_type

					if channel.override:
						if is_bump_map:
							channels_data["bump"] = {
								"intensity_value" : intensity_channel,
								"height" : channel.bump_distance,
								"midlevel" : channel.bump_midlevel,
								"blend" : channel.blend_type,
							}

						source_ch = get_channel_source(channel, layer)
						
						if source_ch:
							ch_image_path = source_ch.image.filepath_from_user()

							if is_bump_map:
								channels_data["bump"]["source"] = bpy.path.basename(ch_image_path)
							else:
								channel_info["source"] = bpy.path.basename(ch_image_path)
						else:
							ch_idx = get_layer_channel_index(layer, channel)
							root_ch = yp.channels[ch_idx]
							if is_bump_map:
								channels_data["bump"]["value"] = channel.override_color[:]
							else:
								if root_ch.type == "VALUE":
									val_ovr = get_entity_prop_value(channel, 'override_value')
									channel_info["value"] = val_ovr
								elif root_ch.type == "RGB":
									color_ovr = get_entity_prop_value(channel, 'override_color')
									channel_info["value"] = color_ovr[:]

					if channel.override_1:								
						source_ch_1 = get_channel_source_1(channel, layer)
						if is_normal_map:
							channel_info["strength"] = channel.normal_strength
							if source_ch_1:
								ch_image_path_1 = source_ch_1.image.filepath_from_user()
								channel_info["source"] = bpy.path.basename(ch_image_path_1)
							else:
								color_ovr = get_entity_prop_value(channel, 'override_1_color')
								channel_info["value"] = color_ovr[:]
						else:
							channel_info = None
						print("channel path 1", id_ch, " = ",ch_image_path_1)

					if ch_image_path != "":
						print("copying ch_image_path", ch_image_path)
						copying_files.append(ch_image_path)

					if ch_image_path_1 != "":
						print("copying ch_image_path_1", ch_image_path_1)
						copying_files.append(ch_image_path_1)

					if channel_info != None:
						channels_data[key_name] = channel_info

				layer_data["channels"] = channels_data
			msk:Mask.YLayerMask
			for idx, msk in enumerate(layer.masks):
				if not msk.enable:
					continue
				
				mask_type = msk.type
				print("mask type ", mask_type)
				mask_data = {
					"type"	: mask_type,
				}

				intensity_mask = get_entity_prop_value(msk, 'intensity_value')


				if mask_type == "IMAGE":

					mask_tree = get_mask_tree(msk)
					mask_source = mask_tree.nodes.get(msk.source)

					mask_image_path = mask_source.image.filepath_from_user()

					if mask_image_path == "":
						mask_image_path = copy_unpack_image(msk.name, my_directory, format_ext)
					else:
						print("mask path exist ", mask_image_path)
						copying_files.append(mask_image_path)

					mask_data["source"] = bpy.path.basename(mask_image_path)

				elif mask_type == "COLOR_ID":
					colorid_col = get_mask_color_id_color(msk)
					mask_data["color"] = [colorid_col[0], colorid_col[1], colorid_col[2], 1.0]
				
				mask_mods = []
				for md in msk.modifiers:
					if not md.enable:
						continue

					new_mod = {
						"type": md.type,
					}
					mask_mods.append(new_mod)

				mask_data["modifiers"] = mask_mods

				mask_data["intensity_value"] = intensity_mask
				mask_data["blend"] = msk.blend_type
				layer_data["masks"].append(mask_data)

				index += 1

			if layer.parent_idx != -1:
				print("add layer to parent ", layer.parent_idx)
				for l in flat_layers:
					if l["id"] == layer.parent_idx:
						l["layers"].append(layer_data)
						print("add layer to parent ", layer.parent_idx)
						break
			else:
				data["layers"].append(layer_data)

			flat_layers.append(layer_data)
	# data["copying_files"] = copying_files
	# Save data to JSON file
	with open(file_path, 'w') as json_file:
		json.dump(data, json_file, indent=4)

	# export mesh as OBJ mesh
	name_asset = bpy.path.display_name_from_filepath(file_path)

	# bpy.ops.export_scene.gltf(export_format='GLTF_SEPARATE', export_apply=True, filepath=os.path.join(my_directory, name_asset + ".glb"), 
	# 						export_vertex_color="ACTIVE", export_tangents=True, use_selection=True, export_texture_dir="gltf_textures")
	obj = bpy.context.active_object
	original_pos = obj.location.copy()
	obj.location = (0, 0, 0)

	bpy.ops.wm.obj_export(filepath=os.path.join(my_directory, name_asset + ".obj"), apply_modifiers=True, export_selected_objects=True, export_materials=False,export_animation=False,export_colors=True)
	obj.location = original_pos

	# copying all textures
	for file in copying_files:
		print("copying file ", file, " to ", my_directory)
		shutil.copy(file, my_directory)

	if pack_file:
		file, ext = os.path.splitext(file_path)
		packed_file = file + filetype_packed
		print(f"Packing files into {packed_file}")
		compress_folder_to_zip(my_directory, packed_file)

		# remove all files except the packed file
		for filename in os.listdir(my_directory):
			file_path = os.path.join(my_directory, filename)
			if file_path != packed_file:
				if os.path.isfile(file_path):
					os.remove(file_path)
				elif os.path.isdir(file_path):
					shutil.rmtree(file_path)
				print(f"Removed: {file_path}")
			else:
				print(f"Kept: {file_path}")
				
def get_modifiers(modifiers):
	ret_modifiers = []
	for m in modifiers:
		if not m.enable:
			continue
		new_mod = {
			"type": m.type,
		}

		mod_tree = get_mod_tree(m)

		if m.type == "INVERT":
			new_mod["r"] = m.invert_r_enable
			new_mod["g"] = m.invert_g_enable
			new_mod["b"] = m.invert_b_enable
			new_mod["a"] = m.invert_a_enable
		elif m.type == "MATH":
			math = mod_tree.nodes.get(m.math)

			# print("math inputs ", math.inputs[0], math.inputs[1], math.inputs[2], math.inputs[3], math.inputs[4], math.inputs[5])

			new_mod["r"] = math.inputs[2].default_value
			new_mod["g"] = math.inputs[3].default_value
			new_mod["b"] = math.inputs[4].default_value
			new_mod["a"] = math.inputs[5].default_value
			new_mod["method"] = m.math_meth
			new_mod["affect_alpha"] = m.affect_alpha

		elif m.type == "BRIGHT_CONTRAST":
			brightcon = mod_tree.nodes.get(m.brightcon)
			new_mod["brightness"] = brightcon.inputs[1].default_value
			new_mod["contrast"] = brightcon.inputs[2].default_value
		elif m.type == "HUE_SATURATION":
			huesat = mod_tree.nodes.get(m.huesat)
			
			new_mod["hue"] = huesat.inputs[0].default_value
			new_mod["saturation"] = huesat.inputs[1].default_value
			new_mod["value"] = huesat.inputs[2].default_value

		ret_modifiers.append(new_mod)
	return ret_modifiers

def copy_unpack_image(image_name, directory, file_format):

	filepath_new = os.path.join(directory, image_name) + file_format
	print("unpack item ",image_name, " to ", filepath_new)

	mask_image = bpy.data.images[image_name]
	override = bpy.context.copy()
	override['edit_image'] = mask_image
	if is_bl_newer_than(4):
		with bpy.context.temp_override(**override):
			bpy.ops.image.save_as(filepath=filepath_new, copy=True, )
	else: bpy.ops.image.save_as(override, filepath=filepath_new)


	return filepath_new


def compress_folder_to_zip(folder_path, zip_file_path):
	import zipfile
	print("write zip file ", zip_file_path, " from ", folder_path)
	with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
		for root, dirs, files in os.walk(folder_path):
			for file in files:
				file_path = os.path.join(root, file)
				if file_path == zip_file_path:
					continue
				arcname = os.path.relpath(file_path, folder_path)
				print("add file ", file_path, " to ", arcname)
				zipf.write(file_path, arcname)

	print(f"Files in {folder_path} have been compressed into {zip_file_path}")

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

classes = [YExporter, YSceneExporter]

def register():
	for cl in classes:
		bpy.utils.register_class(cl)

def unregister():
	for cl in classes:
		bpy.utils.unregister_class(cl)

if __name__ == "__main__":
	register()