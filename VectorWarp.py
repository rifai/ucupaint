import bpy, time
from .common import *
from bpy.props import *

from .node_connections import reconnect_layer_nodes, reconnect_yp_nodes
from .node_arrangements import rearrange_layer_nodes, rearrange_yp_nodes
from .input_outputs import *

def update_warp_nodes_enable(self, context):
    yp = self.id_data.yp
    if yp.halt_update: return
    tree = get_mod_tree(self)

    check_vectorwarp_nodes(self, tree)

    # match1 = re.match(r'yp\.layers\[(\d+)\]\.channels\[(\d+)\]\.warps\[(\d+)\]', self.path_from_id())
    match2 = re.match(r'yp\.layers\[(\d+)\]\.warps\[(\d+)\]', self.path_from_id())
    # match3 = re.match(r'yp\.channels\[(\d+)\]\.warps\[(\d+)\]', self.path_from_id())

    if match2:
        layer = yp.layers[int(match2.group(1))]

        check_layer_tree_ios(layer)

        reconnect_layer_nodes(layer)
        rearrange_layer_nodes(layer)



    # elif match3:
    #     channel = yp.channels[int(match3.group(1))]
    #     reconnect_yp_nodes(self.id_data)
    #     rearrange_yp_nodes(self.id_data)

def update_uniform_scale_enabled(self, context):
    yp = self.id_data.yp
    if yp.halt_update: return

    # match1 = re.match(r'yp\.layers\[(\d+)\]\.channels\[(\d+)\]\.warps\[(\d+)\]', self.path_from_id())
    match2 = re.match(r'yp\.layers\[(\d+)\]\.warps\[(\d+)\]', self.path_from_id())
    # match3 = re.match(r'yp\.channels\[(\d+)\]\.warps\[(\d+)\]', self.path_from_id())

    tree = get_mod_tree(self)


    if match2:
        layer = yp.layers[int(match2.group(1))]

    scale_input = tree.nodes.get(self.mapping).inputs[3]

    if self.uniform_scale_enable:
        set_entity_prop_value(self, 'uniform_scale_value', min(map(abs, scale_input.default_value)))
    else:
        scale = get_entity_prop_value(self, 'uniform_scale_value')
        scale_input.default_value = (scale, scale, scale)

    check_layer_tree_ios(layer)

    reconnect_layer_nodes(layer)
    rearrange_layer_nodes(layer)

    print("uniform scale enabled=", self.uniform_scale_enable, "uniform scale value=", self.uniform_scale_value)

class YVectorWarp(bpy.types.PropertyGroup):
    # todo : new image picker for image warp, mapping (default mix, vector use prev vector)

    enable: BoolProperty(
        name = 'Enable',
        description = 'Enable this warp',
        default = True,
        update=update_warp_nodes_enable,
    )

    name : StringProperty(
        name = 'Warp Name',
        description = 'Warp name',
        default = '',
    )

    type : EnumProperty(
        name = 'Warp Type',
        items = warp_type_items,
        default = 'IMAGE'
    )

    source : StringProperty(default='')

    blend_type : EnumProperty(
        name = 'Blend',
        items = blend_type_items,
        update = update_warp_nodes_enable,
    )

    intensity_value: FloatProperty(name = 'Opacity', default=1.0, min=0.0, max=1.0, subtype='FACTOR', precision=3)

    mix: StringProperty(default='')

    mapping : StringProperty(default='')
    uniform_scale_value : FloatProperty(default=1)
    uniform_scale_enable : BoolProperty(
        name = 'Enable Uniform Scale', 
        description = 'Use the same value for all scale components',
        default = False,
        update = update_uniform_scale_enabled
    )

    image : StringProperty(default='')
    image_name : StringProperty(default='')

    brick : StringProperty(default='')
    checker : StringProperty(default='')
    gradient : StringProperty(default='')
    magic : StringProperty(default='')
    musgrave : StringProperty(default='')
    noise : StringProperty(default='')
    voronoi : StringProperty(default='')
    wave : StringProperty(default='')
    gabor : StringProperty(default='')

    expand_content : BoolProperty(default=True)

def check_vectorwarp_trees(parent, rearrange=False):
    group_tree = parent.id_data
    yp = group_tree.yp

    enable_tree = False
    is_layer = False

    # match1 = re.match(r'^yp\.layers\[(\d+)\]\.channels\[(\d+)\]$', parent.path_from_id())
    match2 = re.match(r'^yp\.layers\[(\d+)\]$', parent.path_from_id())

    # if match1:
    #     layer = yp.layers[int(match1.group(1))]
    #     root_ch = yp.channels[int(match1.group(2))]
    #     ch = parent
    #     name = root_ch.name + ' ' + layer.name
    #     if (
    #         root_ch.type == 'NORMAL' and root_ch.enable_smooth_bump and (
    #             (not ch.override and layer.type not in {'BACKGROUND', 'COLOR', 'OBJECT_INDEX'}) or 
    #             (ch.override and ch.override_type not in {'DEFAULT'} and ch.normal_map_type in {'BUMP_MAP', 'BUMP_NORMAL_MAP'})
    #         )
    #         ):
    #         enable_tree = True
    #     parent_tree = get_tree(layer)
    if match2:
        layer = parent
        name = layer.name
        if layer.type not in {'IMAGE', 'VCOL', 'BACKGROUND', 'COLOR', 'GROUP', 'HEMI', 'MUSGRAVE'}:
            enable_tree = True
        if layer.source_group != '':
            parent_tree = get_source_tree(layer)
        else: parent_tree = get_tree(layer)
        is_layer=True

    else:
        parent_tree = group_tree

    if len(parent.warps) == 0:
        enable_tree = False

    mod_group = None
    if hasattr(parent, 'mod_group'):
        mod_group = parent_tree.nodes.get(parent.mod_group)

    # print("mod_group=", mod_group, "enable_tree=", enable_tree, "is_layer=", 
    #       is_layer, "parent_tree=", parent_tree, "parent=", parent, "name=", name)
    
    if enable_tree:
        if mod_group:
            for mod in parent.warps:
                check_vectorwarp_nodes(mod, mod_group.node_tree)
        else:
            # enable_modifiers_tree(parent, parent_tree, name, is_layer)
            pass
    else:
        if not mod_group:
            for mod in parent.warps:
                check_vectorwarp_nodes(mod, parent_tree)
        else:
            # disable_modifiers_tree(parent, parent_tree)
            pass

    # if rearrange:
    #     reconnect_layer_nodes(layer)
    #     rearrange_layer_nodes(layer)

def delete_vectorwarp_nodes(tree, vw):
    # Delete the mix node
    remove_node(tree, vw, 'mix')
    # Delete the nodes
    remove_node(tree, vw, 'frame')

    match vw.type:
        case 'MAPPING':
            remove_node(tree, vw, 'mapping')
        case 'IMAGE':
            remove_node(tree, vw, 'image')
        case 'BRICK':
            remove_node(tree, vw, 'brick')
        case 'CHECKER':
            remove_node(tree, vw, 'checker')
        case 'GRADIENT':
            remove_node(tree, vw, 'gradient')
        case 'MAGIC':
            remove_node(tree, vw, 'magic')
        case 'MUSGRAVE':
            remove_node(tree, vw, 'musgrave')
        case 'NOISE':
            remove_node(tree, vw, 'noise')
        case 'VORONOI':
            remove_node(tree, vw, 'voronoi')
        case 'WAVE':
            remove_node(tree, vw, 'wave')
        case 'GABOR':
            remove_node(tree, vw, 'gabor')


def check_vectorwarp_nodes(vw:YVectorWarp, tree, ref_tree=None):

    # yp = vw.id_data.yp
    # nodes = tree.nodes

    # print("type=", vw.type)
    # Check the nodes

    field_name = 'mapping'
    node_name = vw.mapping
    node_type = 'ShaderNodeMapping'

    match vw.type:
        case 'MAPPING':
            field_name = 'mapping'
            node_name = vw.mapping
            node_type = 'ShaderNodeMapping'
        case 'IMAGE':
            field_name = 'image'
            node_name = vw.image
            node_type = layer_node_bl_idnames[vw.type]
        case 'BRICK':
            field_name = 'brick'
            node_name = vw.brick
            node_type = layer_node_bl_idnames[vw.type]
        case 'CHECKER':
            field_name = 'checker'
            node_name = vw.checker
            node_type = layer_node_bl_idnames[vw.type]
        case 'GRADIENT':
            field_name = 'gradient'
            node_name = vw.gradient
            node_type = layer_node_bl_idnames[vw.type]
        case 'MAGIC':
            field_name = 'magic'
            node_name = vw.magic
            node_type = layer_node_bl_idnames[vw.type]
        case 'MUSGRAVE':
            field_name = 'musgrave'
            node_name = vw.musgrave
            node_type = layer_node_bl_idnames[vw.type]
        case 'NOISE':
            field_name = 'noise'
            node_name = vw.noise
            node_type = layer_node_bl_idnames[vw.type]
        case 'VORONOI':
            field_name = 'voronoi'
            node_name = vw.voronoi
            node_type = layer_node_bl_idnames[vw.type]
        case 'WAVE':
            field_name = 'wave'
            node_name = vw.wave
            node_type = layer_node_bl_idnames[vw.type]
        case 'GABOR':
            field_name = 'gabor'
            node_name = vw.gabor
            node_type = layer_node_bl_idnames[vw.type]

    if not vw.enable:
        remove_node(tree, vw, 'mix')
        remove_node(tree, vw, field_name)
    else:
        if ref_tree:
            node_ref = ref_tree.nodes.get(vw.mix)
            if node_ref: ref_tree.nodes.remove(node_ref)
            mp = new_node(tree, vw, 'mix', 'ShaderNodeMix', 'Mix')
            
            node_ref = ref_tree.nodes.get(node_name)
            if node_ref: ref_tree.nodes.remove(node_ref)

            current_node = new_node(tree, vw, field_name, node_type)

            dirty = True
        else:
            mp, dirty = check_new_node(tree, vw, 'mix', 'ShaderNodeMix', 'Mix', True)
            current_node, node_dirty = check_new_node(tree, vw, field_name, node_type, '', True)
            dirty = dirty or node_dirty

        # if dirty:
        mp.blend_type = vw.blend_type
        mp.inputs[0].default_value = vw.intensity_value
        mp.data_type = 'RGBA'

        match vw.type:
            case 'IMAGE':
                current_node.image = bpy.data.images.get(vw.image_name)
                
class YNewVectorWarp(bpy.types.Operator):
    bl_idname = "wm.y_new_vector_warp"
    bl_label = "New " + get_addon_title() + " Vector Warp"
    bl_description = "New " + get_addon_title() + " Vector Warp"
    bl_options = {'REGISTER', 'UNDO'}

    type : EnumProperty(
        name = 'Vector Warp Type',
        items = warp_type_items,
        default = 'IMAGE',
    )

    @classmethod
    def poll(cls, context):
        return get_active_ypaint_node() and hasattr(context, 'parent')

    def execute(self, context):
        node = get_active_ypaint_node()
        group_tree = node.node_tree
        yp = group_tree.yp

        parent = context.parent

        path_id = parent.path_from_id()
        print("path id=", path_id)


        m1 = re.match(r'^yp\.layers\[(\d+)\]$', context.parent.path_from_id())
        # m2 = re.match(r'^yp\.layers\[(\d+)\]\.channels\[(\d+)\]$', context.parent.path_from_id())
        # m3 = re.match(r'^yp\.channels\[(\d+)\]$', context.parent.path_from_id())

        if m1: layer = yp.layers[int(m1.group(1))]
        # elif m2: layer = yp.layers[int(m2.group(1))]
        else: layer = None

        new_warp = parent.warps.add()

        name = [mt[1] for mt in warp_type_items if mt[0] == self.type][0]

        new_warp.name = get_unique_name(name, layer.warps)
        new_warp.type = self.type
        new_warp.blend_type = 'ADD'

        if self.type == 'MAPPING':
            new_warp.blend_type = 'MIX'

        check_vectorwarp_trees(parent)

        # Expand channel content to see added modifier
        if m1:
            context.layer_ui.expand_content = True
        # elif m2:
        #     context.layer_ui.channels[int(m2.group(2))].expand_content = True
        # elif m3:
        #     context.channel_ui.expand_content = True

        # print("layer=", layer, "parent=", parent, "new_warp=", new_warp)
        # Reconnect and rearrange nodes
        if layer:
            reconnect_layer_nodes(layer)
            rearrange_layer_nodes(layer)
        else: 
            reconnect_yp_nodes(group_tree)
            rearrange_yp_nodes(group_tree)

        # Update UI
        context.window_manager.ypui.need_update = True

        return {'FINISHED'}

class YMoveYPaintVectorWarp(bpy.types.Operator):
    bl_idname = "wm.y_move_ypaint_vector_warp"
    bl_label = "Move " + get_addon_title() + " Vector Warp"
    bl_description = "Move " + get_addon_title() + " Vector Warp"
    bl_options = {'REGISTER', 'UNDO'}

    direction : EnumProperty(
        name = 'Direction',
        items = (
            ('UP', 'Up', ''),
            ('DOWN', 'Down', '')
        ),
        default = 'UP'
    )

    @classmethod
    def poll(cls, context):
        return (get_active_ypaint_node() and 
                hasattr(context, 'parent') and hasattr(context, 'vector_warp'))

    def execute(self, context):
        node = get_active_ypaint_node()
        group_tree = node.node_tree
        yp = group_tree.yp

        parent = context.parent

        num_mods = len(parent.warps)
        if num_mods < 2: return {'CANCELLED'}

        mod = context.vector_warp
        index = -1
        for i, m in enumerate(parent.warps):
            if m == mod:
                index = i
                break
        if index == -1: return {'CANCELLED'}

        # Get new index
        if self.direction == 'UP' and index > 0:
            new_index = index-1
        elif self.direction == 'DOWN' and index < num_mods-1:
            new_index = index+1
        else:
            return {'CANCELLED'}

        layer = context.layer if hasattr(context, 'layer') else None

        # Swap modifier
        parent.warps.move(index, new_index)
        # swap_modifier_fcurves(parent, index, new_index)

        # Reconnect and rearrange nodes
        if layer: 
            reconnect_layer_nodes(layer)
            rearrange_layer_nodes(layer)
        else: 
            reconnect_yp_nodes(group_tree)
            rearrange_yp_nodes(group_tree)

        # Update UI
        context.window_manager.ypui.need_update = True

        return {'FINISHED'}

class YRemoveYPaintVectorWarp(bpy.types.Operator):
    bl_idname = "wm.y_remove_ypaint_vector_warp"
    bl_label = "Remove " + get_addon_title() + " Vector Warp"
    bl_description = "Remove " + get_addon_title() + " Vector Warp"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return hasattr(context, 'parent') and hasattr(context, 'vector_warp')

    def execute(self, context):
        group_tree = context.parent.id_data
        # yp = group_tree.yp

        parent = context.parent
        vw = context.vector_warp

        index = -1
        for i, m in enumerate(parent.warps):
            if m == vw:
                index = i
                break
        if index == -1: return {'CANCELLED'}

        if len(parent.warps) < 1: return {'CANCELLED'}

        layer = context.layer if hasattr(context, 'layer') else None

        tree = get_mod_tree(parent)

        # Remove modifier fcurves first
        # remove_entity_fcurves(mod)
        # shift_modifier_fcurves_up(parent, index)

        # Delete the nodes
        delete_vectorwarp_nodes(tree, vw)

        # Delete the modifier
        parent.warps.remove(index)

        # Delete modifier pipeline if no modifier left
        #if len(parent.modifiers) == 0:
        #    unset_modifier_pipeline_nodes(tree, parent)

        check_vectorwarp_trees(parent)

        # # Rearrange nodes
        if layer:
            reconnect_layer_nodes(layer)
            rearrange_layer_nodes(layer)
        else: 
            reconnect_yp_nodes(group_tree)
            rearrange_yp_nodes(group_tree)

        # Update UI
        context.window_manager.ypui.need_update = True

        return {'FINISHED'}

class YOpenAvailableImageToVectorWarp(bpy.types.Operator):
    """Open Available Image to Vector Warp"""
    bl_idname = "wm.y_open_available_image_to_vector_warp"
    bl_label = "Open Available Image to Vector Warp"
    bl_options = {'REGISTER', 'UNDO'}

    interpolation : EnumProperty(
        name = 'Image Interpolation Type',
        description = 'Image interpolation type',
        items = interpolation_type_items,
        default = 'Linear'
    )

    blend_type : EnumProperty(
        name = 'Blend',
        items = blend_type_items,
    )

    image_name : StringProperty(name="Image")
    image_coll : CollectionProperty(type=bpy.types.PropertyGroup)

    # layer : PointerProperty(type=YLayer)
    
    @classmethod
    def poll(cls, context):
        print("has parent =", hasattr(context, 'parent'))
        return get_active_ypaint_node() and hasattr(context, 'parent')

    def invoke(self, context, event):
        obj = context.object
        node = get_active_ypaint_node()
        yp = node.node_tree.yp

        self.image_coll.clear()
        imgs = bpy.data.images
        baked_channel_images = get_all_baked_channel_images(node.node_tree)
        for img in imgs:
            if is_image_available_to_open(img) and img not in baked_channel_images:
                self.image_coll.add().name = img.name
        
        print("has parent invoke =", hasattr(context, 'parent'))

        return context.window_manager.invoke_props_dialog(self)

    # def check(self, context):
    #     return True

    def draw(self, context):
        # node = get_active_ypaint_node()
        # yp = node.node_tree.yp
        # obj = context.object

        self.layout.prop_search(self, "image_name", self, "image_coll", icon='IMAGE_DATA')
        row = self.layout.row()

        col = row.column()
        col.label(text='Interpolation:')
        col.label(text='Vector:')

        col = row.column()
        col.prop(self, 'interpolation', text='')
        
        print("has parent draw =", hasattr(context, 'parent'))


    def execute(self, context):
        T = time.time()

        node = get_active_ypaint_node()

        group_tree = node.node_tree

        yp = group_tree.yp

        wm = context.window_manager

        if self.image_name == '':
            self.report({'ERROR'}, "No image selected!")
            return {'CANCELLED'}

        node.node_tree.yp.halt_update = True

        # image = None
        # image = bpy.data.images.get(self.image_name)
        # name = image.name

        parent = context.parent

        # m1 = re.match(r'^yp\.layers\[(\d+)\]$', context.parent.path_from_id())
        # m2 = re.match(r'^yp\.layers\[(\d+)\]\.channels\[(\d+)\]$', context.parent.path_from_id())
        # m3 = re.match(r'^yp\.channels\[(\d+)\]$', context.parent.path_from_id())

        layer = self.layer 
        new_warp = parent.warps.add()

        name = [mt[1] for mt in warp_type_items if mt[0] == self.type][0]

        new_warp.name = get_unique_name(name, layer.warps)
        new_warp.type = 'IMAGE'
        new_warp.blend_type = 'ADD'
        new_warp.image_name = self.image_name

        check_vectorwarp_trees(parent)

        node.node_tree.yp.halt_update = False

        # Reconnect and rearrange nodes
        reconnect_yp_nodes(node.node_tree)
        rearrange_yp_nodes(node.node_tree)

        # Update UI
        wm.ypui.need_update = True

        print('INFO: Image', self.image_name, 'is opened in', '{:0.2f}'.format((time.time() - T) * 1000), 'ms!')
        wm.yptimer.time = str(time.time())

        return {'FINISHED'}
    
classes = (
    YVectorWarp,
    YNewVectorWarp,
    YMoveYPaintVectorWarp,
    YRemoveYPaintVectorWarp,
    YOpenAvailableImageToVectorWarp,
)
         
def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)