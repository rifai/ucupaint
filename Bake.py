import bpy, re, time
from bpy.props import *
from mathutils import *
from .common import *
from .node_connections import *
from .node_arrangements import *
from . import lib

BL28_HACK = True

def remember_before_bake(self, context):
    scene = self.scene
    obj = self.obj
    uv_layers = self.uv_layers
    ypui = context.window_manager.ypui

    # Remember render settings
    self.ori_engine = scene.render.engine
    self.ori_bake_type = scene.cycles.bake_type
    self.ori_samples = scene.cycles.samples
    self.ori_threads_mode = scene.render.threads_mode
    self.ori_margin = scene.render.bake.margin
    self.ori_use_clear = scene.render.bake.use_clear

    # Remember uv
    self.ori_active_uv = uv_layers.active

    # Remember scene objects
    if bpy.app.version_string.startswith('2.8'):
        self.ori_active_selected_objs = [o for o in scene.objects if o.select_get()]
    else: self.ori_active_selected_objs = [o for o in scene.objects if o.select]

    # Remember ypui
    self.ori_disable_temp_uv = ypui.disable_auto_temp_uv_update

def prepare_bake_settings(self, context):
    scene = self.scene
    obj = self.obj
    uv_layers = self.uv_layers
    ypui = context.window_manager.ypui

    scene.render.engine = 'CYCLES'
    scene.cycles.bake_type = 'EMIT'
    scene.cycles.samples = self.samples
    scene.render.threads_mode = 'AUTO'
    scene.render.bake.margin = self.margin
    #scene.render.bake.use_clear = True
    scene.render.bake.use_clear = False

    # Disable other object selections and select only active object
    if bpy.app.version_string.startswith('2.8'):
        for o in scene.objects:
            o.select_set(False)
        obj.select_set(True)
    else:
        for o in scene.objects:
            o.select = False
        obj.select = True

    # Set active uv layers
    uv_layers.active = uv_layers.get(self.uv_map)

    # Disable auto temp uv update
    ypui.disable_auto_temp_uv_update = True

def recover_bake_settings(self, context):
    scene = self.scene
    obj = self.obj
    uv_layers = self.uv_layers
    ypui = context.window_manager.ypui

    scene.render.engine = self.ori_engine
    scene.cycles.bake_type = self.ori_bake_type
    scene.cycles.samples = self.ori_samples
    scene.render.threads_mode = self.ori_threads_mode
    scene.render.bake.margin = self.ori_margin
    scene.render.bake.use_clear = self.ori_use_clear

    # Recover uv
    uv_layers.active = self.ori_active_uv

    # Disable other object selections
    if bpy.app.version_string.startswith('2.8'):
        for o in scene.objects:
            if o in self.ori_active_selected_objs:
                o.select_set(True)
            else: o.select_set(False)
    else:
        for o in scene.objects:
            if o in self.ori_active_selected_objs:
                o.select = True
            else: o.select = False

    # Recover active object
    #scene.objects.active = self.ori_active_obj

    # Recover ypui
    ypui.disable_auto_temp_uv_update = self.ori_disable_temp_uv

def transfer_uv(mat, entity, uv_map):

    #if hasattr(obj.data, 'uv_textures'):
    #    uv_layers = obj.data.uv_textures
    #else: uv_layers = obj.data.uv_layers

    #uv_layers.active = uv_layers.get(uv_map)

    # Check entity
    m1 = re.match(r'^yp\.layers\[(\d+)\]$', entity.path_from_id())
    m2 = re.match(r'^yp\.layers\[(\d+)\]\.masks\[(\d+)\]$', entity.path_from_id())

    if m1: 
        source = get_layer_source(entity)
        mapping = get_layer_mapping(entity)
    elif m2: 
        source = get_mask_source(entity)
        mapping = get_mask_mapping(entity)
    else: return

    image = source.image
    if not image: return

    # Get image settings
    segment = None
    use_alpha = False
    if image.yia.is_image_atlas and entity.segment_name != '':
        segment = image.yia.segments.get(entity.segment_name)
        width = segment.width
        height = segment.height
        if image.yia.color == 'WHITE':
            col = (1.0, 1.0, 1.0, 1.0)
        elif image.yia.color == 'BLACK':
            col = (0.0, 0.0, 0.0, 1.0)
        else: 
            col = (0.0, 0.0, 0.0, 0.0)
            use_alpha = True
    else:
        width = image.size[0]
        height = image.size[1]
        col = (0.0, 0.0, 0.0, 0.0)
        use_alpha = True

    # Create temp image as bake target
    temp_image = bpy.data.images.new(name='__TEMP',
            width=width, height=height) #, alpha=True, float_buffer=hdr)
    temp_image.generated_color = col

    # Create bake nodes
    tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
    emit = mat.node_tree.nodes.new('ShaderNodeEmission')

    # Set image to temp nodes
    src = mat.node_tree.nodes.new('ShaderNodeTexImage')
    src.image = image
    src_uv = mat.node_tree.nodes.new('ShaderNodeUVMap')
    src_uv.uv_map = entity.uv_name

    # Copy mapping
    mapp = mat.node_tree.nodes.new('ShaderNodeMapping')

    mapp.translation[0] = mapping.translation[0]
    mapp.translation[1] = mapping.translation[1]
    mapp.translation[2] = mapping.translation[2]

    mapp.rotation[0] = mapping.rotation[0]
    mapp.rotation[1] = mapping.rotation[1]
    mapp.rotation[2] = mapping.rotation[2]

    mapp.scale[0] = mapping.scale[0]
    mapp.scale[1] = mapping.scale[1]
    mapp.scale[2] = mapping.scale[2]

    # Get material output
    output = get_active_mat_output_node(mat.node_tree)
    ori_bsdf = output.inputs[0].links[0].from_socket

    straight_over = None
    if use_alpha:
        straight_over = mat.node_tree.nodes.new('ShaderNodeGroup')
        straight_over.node_tree = get_node_tree_lib(lib.STRAIGHT_OVER)
        straight_over.inputs[1].default_value = 0.0

    # Set temp image node
    tex.image = temp_image
    mat.node_tree.nodes.active = tex

    # Links
    mat.node_tree.links.new(src_uv.outputs[0], mapp.inputs[0])
    mat.node_tree.links.new(mapp.outputs[0], src.inputs[0])
    rgb = src.outputs[0]
    alpha = src.outputs[1]
    if straight_over:
        mat.node_tree.links.new(rgb, straight_over.inputs[2])
        mat.node_tree.links.new(alpha, straight_over.inputs[3])
        rgb = straight_over.outputs[0]

    mat.node_tree.links.new(rgb, emit.inputs[0])
    mat.node_tree.links.new(emit.outputs[0], output.inputs[0])

    # Bake!
    bpy.ops.object.bake()

    # Copy results to original image
    target_pxs = list(image.pixels)
    temp_pxs = list(temp_image.pixels)

    if segment:
        start_x = width * segment.tile_x
        start_y = height * segment.tile_y
    else:
        start_x = 0
        start_y = 0

    for y in range(height):
        temp_offset_y = width * 4 * y
        offset_y = image.size[0] * 4 * (y + start_y)
        for x in range(width):
            temp_offset_x = 4 * x
            offset_x = 4 * (x + start_x)
            for i in range(3):
                target_pxs[offset_y + offset_x + i] = temp_pxs[temp_offset_y + temp_offset_x + i]

    # Bake alpha if using alpha
    linear = None
    if use_alpha:
        linear = mat.node_tree.nodes.new('ShaderNodeGroup')
        linear.node_tree = get_node_tree_lib(lib.SRGB_2_LINEAR)

        mat.node_tree.links.new(src.outputs[1], linear.inputs[0])
        mat.node_tree.links.new(linear.outputs[0], emit.inputs[0])

        # Bake again!
        bpy.ops.object.bake()

        temp_pxs = list(temp_image.pixels)

        for y in range(height):
            temp_offset_y = width * 4 * y
            offset_y = image.size[0] * 4 * (y + start_y)
            for x in range(width):
                temp_offset_x = 4 * x
                offset_x = 4 * (x + start_x)
                target_pxs[offset_y + offset_x + 3] = temp_pxs[temp_offset_y + temp_offset_x]

    # Copy back edited pixels to original image
    image.pixels = target_pxs

    # Remove temp nodes
    simple_remove_node(mat.node_tree, tex)
    simple_remove_node(mat.node_tree, emit)
    simple_remove_node(mat.node_tree, src)
    simple_remove_node(mat.node_tree, src_uv)
    simple_remove_node(mat.node_tree, mapp)
    if straight_over:
        simple_remove_node(mat.node_tree, straight_over)
    if linear:
        simple_remove_node(mat.node_tree, linear)

    mat.node_tree.links.new(ori_bsdf, output.inputs[0])

    entity.translation = (0.0, 0.0, 0.0)
    entity.rotation = (0.0, 0.0, 0.0)
    entity.scale = (1.0, 1.0, 1.0)

    # Change uv of entity
    entity.uv_name = uv_map

    # Update entity transform
    #update_mapping(entity)

class YTransferSomeLayerUV(bpy.types.Operator):
    bl_idname = "node.y_transfer_some_layer_uv"
    bl_label = "Transfer Some Layer UV"
    bl_description = "Transfer some layers/masks UV by baking it to other uv (this will take quite some time to finish)."
    bl_options = {'REGISTER', 'UNDO'}

    from_uv_map = StringProperty(default='')
    uv_map = StringProperty(default='')
    uv_map_coll = CollectionProperty(type=bpy.types.PropertyGroup)

    samples = IntProperty(name='Bake Samples', 
            description='Bake Samples, more means less jagged on generated textures', 
            default=1, min=1)

    margin = IntProperty(name='Bake Margin',
            description = 'Bake margin in pixels',
            default=5, subtype='PIXEL')

    @classmethod
    def poll(cls, context):
        return get_active_ypaint_node() and context.object.type == 'MESH' # and hasattr(context, 'layer')

    def invoke(self, context, event):
        obj = self.obj = context.object
        scene = self.scene = context.scene

        # Use active uv layer name by default
        if hasattr(obj.data, 'uv_textures'):
            uv_layers = self.uv_layers = obj.data.uv_textures
        else: uv_layers = self.uv_layers = obj.data.uv_layers

        # UV Map collections update
        self.uv_map_coll.clear()
        for uv in uv_layers:
            if not uv.name.startswith(TEMP_UV):
                self.uv_map_coll.add().name = uv.name

        return context.window_manager.invoke_props_dialog(self, width=320)

    def check(self, context):
        return True

    def draw(self, context):

        if bpy.app.version_string.startswith('2.8'):
            row = self.layout.split(factor=0.4)
        else: row = self.layout.split(percentage=0.4)

        col = row.column(align=False)
        col.label(text='From UV:')
        col.label(text='To UV:')
        col.label(text='Samples:')
        col.label(text='Margin:')

        col = row.column(align=False)
        col.prop_search(self, "from_uv_map", self, "uv_map_coll", text='', icon='GROUP_UVS')
        col.prop_search(self, "uv_map", self, "uv_map_coll", text='', icon='GROUP_UVS')
        col.prop(self, 'samples', text='')
        col.prop(self, 'margin', text='')

    def execute(self, context):

        T = time.time()

        if self.from_uv_map == '' or self.uv_map == '':
            self.report({'ERROR'}, "From or To UV Map is cannot be empty!")
            return {'CANCELLED'}

        if self.from_uv_map == self.uv_map:
            self.report({'ERROR'}, "From and To UV is cannot have same value!")
            return {'CANCELLED'}

        mat = get_active_material()
        node = get_active_ypaint_node()
        yp = node.node_tree.yp

        # Prepare bake settings
        remember_before_bake(self, context)
        prepare_bake_settings(self, context)

        for layer in yp.layers:
            #print(layer.name)
            if layer.type == 'IMAGE' and layer.uv_name == self.from_uv_map:
                transfer_uv(mat, layer, self.uv_map)

            for mask in layer.masks:
                if mask.type == 'IMAGE' and mask.uv_name == self.from_uv_map:
                    transfer_uv(mat, mask, self.uv_map)

        #return {'FINISHED'}

        # Recover bake settings
        recover_bake_settings(self, context)

        # Refresh mapping and stuff
        yp.active_layer_index = yp.active_layer_index

        print('INFO: All layer and masks that using', self.from_uv_map, 'is transferred to', self.uv_map, 'at', '{:0.2f}'.format(time.time() - T), 'seconds!')

        return {'FINISHED'}

class YTransferLayerUV(bpy.types.Operator):
    bl_idname = "node.y_transfer_layer_uv"
    bl_label = "Transfer Layer UV"
    bl_description = "Transfer Layer UV by baking it to other uv (this will take quite some time to finish)."
    bl_options = {'REGISTER', 'UNDO'}

    uv_map = StringProperty(default='')
    uv_map_coll = CollectionProperty(type=bpy.types.PropertyGroup)

    samples = IntProperty(name='Bake Samples', 
            description='Bake Samples, more means less jagged on generated textures', 
            default=1, min=1)

    margin = IntProperty(name='Bake Margin',
            description = 'Bake margin in pixels',
            default=5, subtype='PIXEL')

    @classmethod
    def poll(cls, context):
        return get_active_ypaint_node() and context.object.type == 'MESH' # and hasattr(context, 'layer')

    def invoke(self, context, event):
        obj = self.obj = context.object
        scene = self.scene = context.scene

        if hasattr(context, 'mask'):
            self.entity = context.mask

        elif hasattr(context, 'layer'):
            self.entity = context.layer

        if not self.entity:
            return self.execute(context)

        # Use active uv layer name by default
        if hasattr(obj.data, 'uv_textures'):
            uv_layers = self.uv_layers = obj.data.uv_textures
        else: uv_layers = self.uv_layers = obj.data.uv_layers

        # UV Map collections update
        self.uv_map_coll.clear()
        for uv in uv_layers:
            if not uv.name.startswith(TEMP_UV) and uv.name != self.entity.uv_name:
                self.uv_map_coll.add().name = uv.name

        return context.window_manager.invoke_props_dialog(self, width=320)

    def check(self, context):
        return True

    def draw(self, context):
        if bpy.app.version_string.startswith('2.8'):
            row = self.layout.split(factor=0.4)
        else: row = self.layout.split(percentage=0.4)

        col = row.column(align=False)
        col.label(text='Target UV:')
        col.label(text='Samples:')
        col.label(text='Margin:')

        col = row.column(align=False)
        col.prop_search(self, "uv_map", self, "uv_map_coll", text='', icon='GROUP_UVS')
        col.prop(self, 'samples', text='')
        col.prop(self, 'margin', text='')

    def execute(self, context):
        T = time.time()

        if not hasattr(self, 'entity'):
            return {'CANCELLED'}

        if self.entity.type != 'IMAGE' or self.entity.texcoord_type != 'UV':
            self.report({'ERROR'}, "Only works with image layer/mask with UV Mapping")
            return {'CANCELLED'}

        if self.uv_map == '':
            self.report({'ERROR'}, "Target UV Map cannot be empty!")
            return {'CANCELLED'}

        if self.uv_map == self.entity.uv_name:
            self.report({'ERROR'}, "This layer/mask already use " + self.uv_map + "!")
            return {'CANCELLED'}

        mat = get_active_material()
        yp = self.entity.id_data.yp

        # Prepare bake settings
        remember_before_bake(self, context)
        prepare_bake_settings(self, context)

        # Transfer UV
        transfer_uv(mat, self.entity, self.uv_map)

        # Recover bake settings
        recover_bake_settings(self, context)

        # Refresh mapping and stuff
        yp.active_layer_index = yp.active_layer_index

        print('INFO:', self.entity.name, 'UV is transferred from', self.entity.uv_name, 'to', self.uv_map, 'at', '{:0.2f}'.format(time.time() - T), 'seconds!')

        return {'FINISHED'}

class YBakeChannels(bpy.types.Operator):
    """Bake Channels to Image(s)"""
    bl_idname = "node.y_bake_channels"
    bl_label = "Bake channels to Image"
    bl_options = {'REGISTER', 'UNDO'}

    width = IntProperty(name='Width', default = 1024, min=1, max=4096)
    height = IntProperty(name='Height', default = 1024, min=1, max=4096)

    uv_map = StringProperty(default='')
    uv_map_coll = CollectionProperty(type=bpy.types.PropertyGroup)

    samples = IntProperty(name='Bake Samples', 
            description='Bake Samples, more means less jagged on generated textures', 
            default=1, min=1)

    margin = IntProperty(name='Bake Margin',
            description = 'Bake margin in pixels',
            default=5, subtype='PIXEL')

    @classmethod
    def poll(cls, context):
        return get_active_ypaint_node() and context.object.type == 'MESH'

    def invoke(self, context, event):
        node = get_active_ypaint_node()
        yp = node.node_tree.yp
        obj = self.obj = context.object
        scene = self.scene = context.scene

        # Use active uv layer name by default
        if hasattr(obj.data, 'uv_textures'):
            uv_layers = self.uv_layers = obj.data.uv_textures
        else: uv_layers = self.uv_layers = obj.data.uv_layers

        # Use active uv layer name by default
        if obj.type == 'MESH' and len(uv_layers) > 0:
            active_name = uv_layers.active.name
            if active_name == TEMP_UV:
                self.uv_map = yp.layers[yp.active_layer_index].uv_name
            else: self.uv_map = uv_layers.active.name

            # UV Map collections update
            self.uv_map_coll.clear()
            for uv in uv_layers:
                if not uv.name.startswith(TEMP_UV):
                    self.uv_map_coll.add().name = uv.name

        return context.window_manager.invoke_props_dialog(self, width=320)

    def check(self, context):
        return True

    def draw(self, context):
        if bpy.app.version_string.startswith('2.8'):
            row = self.layout.split(factor=0.4)
        else: row = self.layout.split(percentage=0.4)
        col = row.column(align=True)

        col.label(text='Width:')
        col.label(text='Height:')
        col.separator()
        col.label(text='Samples:')
        col.label(text='Margin:')
        col.separator()
        col.label(text='UV Map:')

        col = row.column(align=True)

        col.prop(self, 'width', text='')
        col.prop(self, 'height', text='')
        col.separator()

        col.prop(self, 'samples', text='')
        col.prop(self, 'margin', text='')
        col.separator()

        col.prop_search(self, "uv_map", self, "uv_map_coll", text='', icon='GROUP_UVS')

    def execute(self, context):

        T = time.time()

        mat = get_active_material()
        node = get_active_ypaint_node()
        tree = node.node_tree
        yp = tree.yp
        obj = context.object

        remember_before_bake(self, context)

        if BL28_HACK: # and bpy.app.version_string.startswith('2.8'):

            self.temp_vcol_ids = []
            uvs = [uv for uv in self.uv_layers if not uv.name.startswith(TEMP_UV)]

            if len(uvs) > MAX_VERTEX_DATA - len(obj.data.vertex_colors):
                self.report({'ERROR'}, "Maximum vertex colors reached! Need at least " + str(len(uvs)) + " vertex color(s)!")
                return {'CANCELLED'}

            # Create vertex color
            for uv in uvs:
                self.uv_layers.active = uv

                obj.data.calc_tangents()

                vcol = obj.data.vertex_colors.new(name='__sign_' + uv.name)
                self.temp_vcol_ids.append(len(obj.data.vertex_colors)-1)

                i = 0
                for poly in obj.data.polygons:
                    for idx in poly.loop_indices:
                        vert = obj.data.loops[idx]
                        bs = vert.bitangent_sign
                        if bpy.app.version_string.startswith('2.8'):
                            vcol.data[i].color = (bs, bs, bs, 1.0)
                        else: vcol.data[i].color = (bs, bs, bs)
                        i += 1

                bt_tree = get_node_tree_lib(lib.TEMP_BITANGENT)
                bt_tree.name = '__bitangent_' + uv.name
                bt_attr = bt_tree.nodes.get('_tangent_sign')
                bt_attr.attribute_name = vcol.name
                t_attr = bt_tree.nodes.get('_tangent')
                t_attr.uv_map = uv.name

                # Replace tangent and bitangent of all layer and masks
                for layer in yp.layers:
                    layer_tree = get_tree(layer)

                    if layer.uv_name == uv.name:

                        tangent = replace_new_node(layer_tree, layer, 'tangent', 'ShaderNodeTangent', 'Tangent')
                        tangent.direction_type = 'UV_MAP'
                        tangent.uv_map = uv.name

                        bitangent = replace_new_node(
                                layer_tree, layer, 'bitangent', 'ShaderNodeGroup', 'Bitangent', bt_tree.name)

                    for mask in layer.masks:

                        if mask.uv_name == uv.name:

                            tangent = layer_tree.nodes.get(mask.tangent)
                            if tangent:
                                tangent = replace_new_node(layer_tree, mask, 'tangent', 'ShaderNodeTangent', 'Tangent')
                                tangent.direction_type = 'UV_MAP'
                                tangent.uv_map = uv.name

                            bitangent = layer_tree.nodes.get(mask.bitangent)
                            if bitangent:
                                bitangent = replace_new_node(
                                        layer_tree, mask, 'bitangent', 'ShaderNodeGroup', 'Bitangent', bt_tree.name)

            # Rearrange nodes
            for layer in yp.layers:
                reconnect_layer_nodes(layer)
                rearrange_layer_nodes(layer)

        #return {'FINISHED'}

        # Disable use baked first
        if yp.use_baked:
            yp.use_baked = False

        # Prepare bake settings
        prepare_bake_settings(self, context)

        # Create nodes
        tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
        emit = mat.node_tree.nodes.new('ShaderNodeEmission')

        linear = mat.node_tree.nodes.new('ShaderNodeGroup')
        linear.node_tree = get_node_tree_lib(lib.SRGB_2_LINEAR)

        norm = mat.node_tree.nodes.new('ShaderNodeGroup')
        norm.node_tree = get_node_tree_lib(lib.BAKE_NORMAL)

        t = norm.node_tree.nodes.get('_tangent')
        t.uv_map = self.uv_map
        
        bt = norm.node_tree.nodes.get('_bitangent')
        bt.uv_map = self.uv_map

        if BL28_HACK:
            socket = bt.outputs[0].links[0].to_socket
            hack_bt = norm.node_tree.nodes.new('ShaderNodeGroup')
            hack_bt.node_tree = bpy.data.node_groups.get('__bitangent_' + self.uv_map)
            create_link(norm.node_tree, hack_bt.outputs[0], socket)

        # Set tex as active node
        mat.node_tree.nodes.active = tex

        # Get output node and remember original bsdf input
        output = get_active_mat_output_node(mat.node_tree)
        ori_bsdf = output.inputs[0].links[0].from_socket

        # Connect emit to output material
        mat.node_tree.links.new(emit.outputs[0], output.inputs[0])

        for ch in yp.channels:

            img_name = tree.name + ' ' + ch.name
            filepath = ''

            # Set nodes
            baked = tree.nodes.get(ch.baked)
            if not baked:
                baked = new_node(tree, ch, 'baked', 'ShaderNodeTexImage', 'Baked ' + ch.name)
            if ch.colorspace == 'LINEAR' or ch.type == 'NORMAL':
                baked.color_space = 'NONE'
            else: baked.color_space = 'COLOR'
            
            # Get uv map
            baked_uv = tree.nodes.get(BAKED_UV)
            if not baked_uv:
                baked_uv = tree.nodes.new('ShaderNodeUVMap')
                baked_uv.name = BAKED_UV

            # Set uv map
            baked_uv.uv_map = self.uv_map

            # Normal related nodes
            if ch.type == 'NORMAL':
                baked_normal = tree.nodes.get(ch.baked_normal)
                if not baked_normal:
                    baked_normal = new_node(tree, ch, 'baked_normal', 'ShaderNodeNormalMap', 'Baked Normal')
                baked_normal.uv_map = self.uv_map

            # Check if image is available
            img_users = []
            if baked.image:
                img_name = baked.image.name
                filepath = baked.image.filepath
                baked.image.name = '____TEMP'
                #if baked.image.users == 1:
                #    bpy.data.images.remove(baked.image)

            #Create new image
            img = bpy.data.images.new(name=img_name,
                    width=self.width, height=self.height) #, alpha=True, float_buffer=self.hdr)
            img.generated_type = 'BLANK'
            img.use_alpha = True
            if ch.type == 'NORMAL':
                img.generated_color = (0.5, 0.5, 1.0, 1.0)
            elif ch.type == 'VALUE':
                val = node.inputs[ch.io_index].default_value
                img.generated_color = (val, val, val, 1.0)
            elif ch.enable_alpha:
                img.generated_color = (0.0, 0.0, 0.0, 1.0)
            else:
                col = node.inputs[ch.io_index].default_value
                col = Color((col[0], col[1], col[2]))
                col = linear_to_srgb(col)
                img.generated_color = (col.r, col.g, col.b, 1.0)

            # Set filepath
            if filepath != '':
                img.filepath = filepath

            # Set image to tex node
            tex.image = img

            # Links to bake
            rgb = node.outputs[ch.io_index]
            if ch.type == 'NORMAL':
                rgb = create_link(mat.node_tree, rgb, norm.inputs[0])[0]
            if ch.colorspace == 'LINEAR' or ch.type == 'NORMAL': # and not bpy.app.version_string.startswith('2.8'):
                rgb = create_link(mat.node_tree, rgb, linear.inputs[0])[0]
            mat.node_tree.links.new(rgb, emit.inputs[0])

            # Bake!
            bpy.ops.object.bake()

            # Bake alpha
            if ch.type == 'RGB' and ch.enable_alpha:
                # Create temp image
                alpha_img = bpy.data.images.new(name='__TEMP__', width=self.width, height=self.height) 

                # Bake setup
                create_link(mat.node_tree, node.outputs[ch.io_index+1], linear.inputs[0])
                create_link(mat.node_tree, linear.outputs[0], emit.inputs[0])
                tex.image = alpha_img

                # Bake
                bpy.ops.object.bake()

                # Copy alpha pixels to main image alpha channel
                img_pxs = list(img.pixels)
                alp_pxs = list(alpha_img.pixels)

                for y in range(self.height):
                    offset_y = self.width * 4 * y
                    for x in range(self.width):
                        a = alp_pxs[offset_y + (x*4)]
                        #a = srgb_to_linear_per_element(a)
                        img_pxs[offset_y + (x*4) + 3] = a

                img.pixels = img_pxs

                # Remove temp image
                bpy.data.images.remove(alpha_img)

            # Set image to baked node and replace all previously original users
            if baked.image:
                temp = baked.image
                img_users = get_all_image_users(baked.image)
                for user in img_users:
                    user.image = img
                bpy.data.images.remove(temp)
            else:
                baked.image = img

        #return {'FINISHED'}

        # Remove temp bake nodes
        simple_remove_node(mat.node_tree, tex)
        simple_remove_node(mat.node_tree, linear)
        simple_remove_node(mat.node_tree, emit)
        simple_remove_node(mat.node_tree, norm)

        # Recover original bsdf
        mat.node_tree.links.new(ori_bsdf, output.inputs[0])

        # Recover bake settings
        recover_bake_settings(self, context)

        # Use bake results
        yp.use_baked = True

        # Recover hack
        if BL28_HACK: # and bpy.app.version_string.startswith('2.8'):

            uvs = [uv for uv in self.uv_layers if not uv.name.startswith(TEMP_UV)]

            # Recover tangent and bitangent
            for uv in uvs:
                for layer in yp.layers:
                    layer_tree = get_tree(layer)

                    if layer.uv_name == uv.name:

                        tangent = replace_new_node(
                                layer_tree, layer, 'tangent', 'ShaderNodeNormalMap', 'Tangent')
                        tangent.uv_map = uv.name
                        tangent.inputs[1].default_value = (1.0, 0.5, 0.5, 1.0)

                        bitangent = replace_new_node(
                                layer_tree, layer, 'bitangent', 'ShaderNodeNormalMap', 'Bitangent')
                        bitangent.uv_map = uv.name
                        bitangent.inputs[1].default_value = (0.5, 1.0, 0.5, 1.0)

                    for mask in layer.masks:

                        if mask.uv_name == uv.name:

                            tangent = layer_tree.nodes.get(mask.tangent)
                            if tangent:
                                tangent = replace_new_node(
                                        layer_tree, mask, 'tangent', 'ShaderNodeNormalMap', 'Tangent')
                                tangent.uv_map = uv.name
                                tangent.inputs[1].default_value = (1.0, 0.5, 0.5, 1.0)

                            bitangent = layer_tree.nodes.get(mask.bitangent)
                            if bitangent:
                                bitangent = replace_new_node(
                                        layer_tree, mask, 'bitangent', 'ShaderNodeNormalMap', 'Bitangent')
                                bitangent.uv_map = uv.name
                                bitangent.inputs[1].default_value = (0.5, 1.0, 0.5, 1.0)

            # Remove vertex color
            for vcol_id in reversed(self.temp_vcol_ids):
                obj.data.vertex_colors.remove(obj.data.vertex_colors[vcol_id])

            # Rearrange nodes
            for layer in yp.layers:
                reconnect_layer_nodes(layer)
                rearrange_layer_nodes(layer)

        # Rearrange
        rearrange_yp_nodes(tree)
        reconnect_yp_nodes(tree)

        print('INFO:', tree.name, 'channels is baked at', '{:0.2f}'.format(time.time() - T), 'seconds!')

        return {'FINISHED'}

#class YDisableBakeResult(bpy.types.Operator):
#    """Disable Baked Image Result"""
#    bl_idname = "node.y_disable_baked_result"
#    bl_label = "Disable Bake Result"
#    bl_options = {'REGISTER', 'UNDO'}
#
#    @classmethod
#    def poll(cls, context):
#        node = get_active_ypaint_node()
#        return node and node.node_tree.yp.use_baked
#
#    def execute(self, context):
#        node = get_active_ypaint_node()
#        tree = node.node_tree
#        yp = tree.yp
#
#        yp.use_baked = False
#
#        reconnect_yp_nodes(tree)
#
#        return {'FINISHED'}

def update_use_baked(self, context):
    tree = self.id_data
    reconnect_yp_nodes(tree)

    # Trigger active image update
    if self.use_baked:
        self.active_channel_index = self.active_channel_index
    else:
        self.active_layer_index = self.active_layer_index

def register():
    bpy.utils.register_class(YTransferSomeLayerUV)
    bpy.utils.register_class(YTransferLayerUV)
    bpy.utils.register_class(YBakeChannels)
    #bpy.utils.register_class(YDisableBakeResult)

def unregister():
    bpy.utils.unregister_class(YTransferSomeLayerUV)
    bpy.utils.unregister_class(YTransferLayerUV)
    bpy.utils.unregister_class(YBakeChannels)
    #bpy.utils.unregister_class(YDisableBakeResult)