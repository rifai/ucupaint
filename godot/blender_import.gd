extends SceneTree


func _init():
	print("init blender_import")


	var args = OS.get_cmdline_user_args()

	print("argss "+str(args))
	if args.size() == 0:
		print("No arguments passed")
		quit()
		return 

	for arg in args:
		print(arg)

	var asset_dir = "res://" + args[1]
	var name_asset = args[0]

	var new_material = ShaderMaterial.new()
	var shader = load(asset_dir+"/%s.gdshader" % name_asset)

	# set shader to material
	new_material.shader = shader

	var dict = {}
	for i in range(1, round(args.size())/2):
		var idx_key = i * 2
		var idx_val = idx_key + 1
		dict[args[idx_key]] = args[idx_val]
	print(dict)

	for key in dict:
		new_material.set_shader_parameter(key, load(asset_dir+"/"+dict[key]))

	ResourceSaver.save(new_material, asset_dir+"/%s.tres" % name_asset)
	quit()


