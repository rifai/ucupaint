import bpy, time
from .common import *
from bpy.props import *

from .node_connections import reconnect_layer_nodes, reconnect_yp_nodes
from .node_arrangements import rearrange_layer_nodes, rearrange_yp_nodes
from .input_outputs import *
from . import UDIM, ListItem

def update_warp_nodes_enable(self, context):
    yp = self.id_data.yp
    if yp.halt_update: return
    tree = get_vw_tree(self)

    check_vectorwarp_nodes(self, tree)

    match1 = re.match(r'yp\.layers\[(\d+)\]\.masks\[(\d+)\]\.warps\[(\d+)\]', self.path_from_id())
    match2 = re.match(r'yp\.layers\[(\d+)\]\.warps\[(\d+)\]', self.path_from_id())
    # match3 = re.match(r'yp\.channels\[(\d+)\]\.warps\[(\d+)\]', self.path_from_id())

    if match2 or match1:
        if match1: layer = yp.layers[int(match1.group(1))]
        else: layer = yp.layers[int(match2.group(1))]

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

    match1 = re.match(r'yp\.layers\[(\d+)\]\.masks\[(\d+)\]\.warps\[(\d+)\]', self.path_from_id())
    match2 = re.match(r'yp\.layers\[(\d+)\]\.warps\[(\d+)\]', self.path_from_id())
    # match3 = re.match(r'yp\.channels\[(\d+)\]\.warps\[(\d+)\]', self.path_from_id())

    tree = get_vw_tree(self)

    if match2:
        layer = yp.layers[int(match2.group(1))]
    elif match1:
        layer = yp.layers[int(match1.group(1))]

    scale_input = tree.nodes.get(self.node).inputs[3]

    if self.uniform_scale_enable:
        set_entity_prop_value(self, 'uniform_scale_value', min(map(abs, scale_input.default_value)))
    else:
        scale = get_entity_prop_value(self, 'uniform_scale_value')
        scale_input.default_value = (scale, scale, scale)

    check_layer_tree_ios(layer)

    reconnect_layer_nodes(layer)
    rearrange_layer_nodes(layer)

def update_blur_vector_factor(self, context):
    yp = self.id_data.yp
    if yp.halt_update: return

    match1 = re.match(r'yp\.layers\[(\d+)\]\.masks\[(\d+)\]\.warps\[(\d+)\]', self.path_from_id())
    match2 = re.match(r'yp\.layers\[(\d+)\]\.warps\[(\d+)\]', self.path_from_id())

    if match2:
        layer = yp.layers[int(match2.group(1))]
    elif match1:
        layer = yp.layers[int(match1.group(1))]

    tree = get_tree(layer)

    blur_vector = tree.nodes.get(self.node) 

    if self.type == 'BLUR' and blur_vector:
        blur_vector.inputs[0].default_value = self.blur_vector_factor

def update_uv_name(self, context):
    yp = self.id_data.yp
    if yp.halt_update: return

    match1 = re.match(r'yp\.layers\[(\d+)\]\.masks\[(\d+)\]\.warps\[(\d+)\]', self.path_from_id())
    match2 = re.match(r'yp\.layers\[(\d+)\]\.warps\[(\d+)\]', self.path_from_id())

    if match2:
        layer = yp.layers[int(match2.group(1))]
    elif match1:
        layer = yp.layers[int(match1.group(1))]

    active_layer = yp.layers[yp.active_layer_index]

    tree = get_tree(layer)

    obj = context.object
    mat = obj.active_material
    group_tree = layer.id_data

    nodes = tree.nodes

    # Use first uv if temp uv or empty is selected
    if self.uv_name in {TEMP_UV, ''}:
        if len(yp.uvs) > 0:
            for uv in yp.uvs:
                self.uv_name = uv.name
                break

    # Update uv layer
    # if obj.type == 'MESH' and not any([m for m in layer.masks if m.active_edit]) and layer == active_layer:

    #     if layer.segment_name != '':
    #         refresh_temp_uv(obj, layer)
    #     else:
    #         uv_layers = get_uv_layers(obj)
    #         uv_layers.active = uv_layers.get(layer.uv_name)

    #         if is_layer_vdm(layer):
    #             uv_layers.active.active_render = True

    #     # Check for other objects with same material
    #     check_uvmap_on_other_objects_with_same_mat(mat, layer.uv_name)

    # Update global uv
    check_uv_nodes(yp)

    # Update uv neighbor
    # smooth_bump_ch = get_smooth_bump_channel(layer)
    # if smooth_bump_ch and smooth_bump_ch.enable and (smooth_bump_ch.normal_map_type in {'BUMP_MAP', 'BUMP_NORMAL_MAP'} or smooth_bump_ch.enable_transition_bump):
    #     uv_neighbor = replace_new_node(
    #         tree, layer, 'uv_neighbor', 'ShaderNodeGroup', 'Neighbor UV', 
    #         lib.get_neighbor_uv_tree_name(layer.texcoord_type, entity=layer), 
    #         return_status=False, hard_replace=True
    #     )
    #     set_uv_neighbor_resolution(layer, uv_neighbor)
    #     if smooth_bump_ch.override and smooth_bump_ch.override_type != 'DEFAULT':
    #         uv_neighbor = replace_new_node(
    #             tree, smooth_bump_ch, 'uv_neighbor', 'ShaderNodeGroup', 'Neighbor UV', 
    #             lib.get_neighbor_uv_tree_name(layer.texcoord_type, entity=layer), 
    #             return_status=False, hard_replace=True
    #         )
    #         set_uv_neighbor_resolution(smooth_bump_ch, uv_neighbor)

    #     # Update neighbor uv if mask bump is active
    #     for i, mask in enumerate(layer.masks):
    #         check_mask_uv_neighbor(tree, layer, mask, i)

    # # Update normal process uv
    # normal_ch = get_height_channel(layer)
    # if normal_ch:
    #     normal_proc = nodes.get(normal_ch.normal_proc)
    #     if hasattr(normal_proc, 'uv_map'):
    #         normal_proc.uv_map = layer.uv_name

    # Update layer tree inputs
    check_layer_tree_ios(layer, tree)

    #if yp_dirty or layer_dirty: #and not yp.halt_reconnect:
    reconnect_layer_nodes(layer)
    rearrange_layer_nodes(layer)

    # Update layer tree inputs
    #if yp_dirty:
    reconnect_yp_nodes(group_tree)
    rearrange_yp_nodes(group_tree)

def update_texcoord_type(self, context):
    yp = self.id_data.yp
    if yp.halt_update: return

    match1 = re.match(r'yp\.layers\[(\d+)\]\.masks\[(\d+)\]\.warps\[(\d+)\]', self.path_from_id())
    match2 = re.match(r'yp\.layers\[(\d+)\]\.warps\[(\d+)\]', self.path_from_id())

    if match2:
        layer = yp.layers[int(match2.group(1))]
    elif match1:
        layer = yp.layers[int(match1.group(1))]

    tree = get_tree(layer)

    if yp.halt_update: return

    # Update global uv
    check_uv_nodes(yp)

    # Update uv neighbor
    # smooth_bump_ch = get_smooth_bump_channel(layer)
    # if smooth_bump_ch and smooth_bump_ch.enable and (smooth_bump_ch.normal_map_type in {'BUMP_MAP', 'BUMP_NORMAL_MAP'} or smooth_bump_ch.enable_transition_bump):
    #     uv_neighbor = replace_new_node(
    #         tree, layer, 'uv_neighbor', 'ShaderNodeGroup', 'Neighbor UV', 
    #         lib.get_neighbor_uv_tree_name(layer.texcoord_type, entity=layer), hard_replace=True
    #     )
    #     set_uv_neighbor_resolution(layer, uv_neighbor)
    #     if smooth_bump_ch.override and smooth_bump_ch.override_type != 'DEFAULT':
    #         uv_neighbor = replace_new_node(
    #             tree, smooth_bump_ch, 'uv_neighbor', 'ShaderNodeGroup', 'Neighbor UV', 
    #             lib.get_neighbor_uv_tree_name(layer.texcoord_type, entity=layer), hard_replace=True
    #         )
    #         set_uv_neighbor_resolution(smooth_bump_ch, uv_neighbor)

    # Update layer tree inputs
    #check_layer_tree_ios(layer, tree)
    check_all_layer_channel_io_and_nodes(layer, tree)

    # Check layer projections
    check_layer_projections(layer)

    #if not yp.halt_reconnect:
    reconnect_layer_nodes(layer)
    rearrange_layer_nodes(layer)

    # Update layer tree inputs
    #if yp_dirty:
    reconnect_yp_nodes(layer.id_data)
    rearrange_yp_nodes(layer.id_data)


def update_active_edit(self, context):
    yp = self.id_data.yp
    if yp.halt_update: return

    match1 = re.match(r'yp\.layers\[(\d+)\]\.masks\[(\d+)\]\.warps\[(\d+)\]', self.path_from_id())
    match2 = re.match(r'yp\.layers\[(\d+)\]\.warps\[(\d+)\]', self.path_from_id())

    if match2:
        layer_idx = int(match2.group(1))
        layer = yp.layers[layer_idx]
    elif match1:
        layer_idx = int(match1.group(1))
        layer = yp.layers[layer_idx]
    else:
        # If not a layer warp, do nothing
        return

    # Disable other active edits
    if self.active_edit: 
        yp.halt_update = True
        for c in layer.channels:
            c.active_edit = False
            c.active_edit_1 = False

        for m in layer.masks:
            m.active_edit = False

            for vw in m.warps:
                if vw != self:
                    vw.active_edit = False

        for vw in layer.warps:
            if vw != self:
                vw.active_edit = False
        
        yp.halt_update = False

    # Refresh
    yp.active_layer_index = layer_idx

    # Set active subitem
    ListItem.set_active_entity_item(self)

class YVectorWarpCache(bpy.types.PropertyGroup):
    type : EnumProperty(
        name = 'Warp Type',
        items = warp_type_items,
        default = 'IMAGE'
    )


class YVectorWarp(bpy.types.PropertyGroup):

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

    texcoord_type : EnumProperty(
        name = 'Layer Coordinate Type',
        description = 'Layer Coordinate Type',
        items = texcoord_type_items,
        default = 'UV',
        update = update_texcoord_type
    )

    uv_name : StringProperty(
        name = 'UV Name',
        description = 'UV Name to use for layer coordinate',
        default = '',
        update = update_uv_name
    )

    # source : StringProperty(default='')
    active_edit : BoolProperty(
        name = 'Active Edit',
        description = 'Enable active edit mode for this warp',
        default = False,
        update = update_active_edit
    )

    blend_type : EnumProperty(
        name = 'Blend',
        items = blend_type_items,
        update = update_warp_nodes_enable,
    )

    intensity_value: FloatProperty(name = 'Opacity', default=1.0, min=0.0, max=1.0, subtype='FACTOR', precision=3)

    mix: StringProperty(default='')
    map_range: StringProperty(default='')

    mapping : StringProperty(default='')
    uniform_scale_value : FloatProperty(default=1)
    uniform_scale_enable : BoolProperty(
        name = 'Enable Uniform Scale', 
        description = 'Use the same value for all scale components',
        default = False,
        update = update_uniform_scale_enabled
    )

    blur_vector_factor : FloatProperty(
        name = 'Blur Vector Factor', 
        description = 'Blur vector factor',
        default=1.0, min=0.0, max=100.0,
        update = update_blur_vector_factor
    )

    node : StringProperty(default='')

    image_name : StringProperty(default='')

    cache_nodes : CollectionProperty(type=YVectorWarpCache)

    expand_content : BoolProperty(default=True)
    
    expand_blend : BoolProperty(default=False)
    expand_source : BoolProperty(default=False)
    expand_vector : BoolProperty(default=False)

def check_vectorwarp_trees(parent, rearrange=False):
    group_tree = parent.id_data
    yp = group_tree.yp

    enable_tree = False
    is_layer = False

    match1 = re.match(r'^yp\.layers\[(\d+)\]\.masks\[(\d+)\]$', parent.path_from_id())
    match2 = re.match(r'^yp\.layers\[(\d+)\]$', parent.path_from_id())

    if match1:
        layer = yp.layers[int(match1.group(1))]
        # root_ch = yp.channels[int(match1.group(2))]
        # ch = parent
        # name = root_ch.name + ' ' + layer.name
        # if (
        #     root_ch.type == 'NORMAL' and root_ch.enable_smooth_bump and (
        #         (not ch.override and layer.type not in {'BACKGROUND', 'COLOR', 'OBJECT_INDEX'}) or 
        #         (ch.override and ch.override_type not in {'DEFAULT'} and ch.normal_map_type in {'BUMP_MAP', 'BUMP_NORMAL_MAP'})
        #     )
        #     ):
        #     enable_tree = True
        parent_tree = get_tree(layer)
    elif match2:
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
    # Delete the map range node
    remove_node(tree, vw, 'map_range')
    # Delete the nodes
    remove_node(tree, vw, 'frame')

    remove_node(tree, vw, 'node')

def check_vectorwarp_extra_nodes(vw, tree, ref_tree):
    if not vw.enable:
        remove_node(tree, vw, 'mix')
        remove_node(tree, vw, 'map_range')
    else:
        is_rangeable = vw.type not in {'MAPPING', 'BLUR'}
        if ref_tree:
            node_ref = ref_tree.nodes.get(vw.mix)
            if node_ref: ref_tree.nodes.remove(node_ref)
            mp = new_node(tree, vw, 'mix', 'ShaderNodeMix', 'Mix')

            node_ref = ref_tree.nodes.get(vw.map_range)
            if node_ref: ref_tree.nodes.remove(node_ref)
            if is_rangeable:
                mr = new_node(tree, vw, 'map_range', 'ShaderNodeMapRange', 'Map Range')
        else:
            mp = check_new_node(tree, vw, 'mix', 'ShaderNodeMix', 'Mix')
            if is_rangeable:
                mr = check_new_node(tree, vw, 'map_range', 'ShaderNodeMapRange', 'Map Range')

        mp.blend_type = vw.blend_type
        mp.inputs[0].default_value = vw.intensity_value
        mp.data_type = 'RGBA'

        if is_rangeable:
            mr.data_type = 'FLOAT_VECTOR'
            mr.inputs["To Min"].default_value = (-0.5, -0.5, -0.5)
            mr.inputs["To Max"].default_value = (0.5, 0.5, 0.5)

def check_vectorwarp_nodes(vw:YVectorWarp, tree, ref_tree=None):

    node_type = 'ShaderNodeMapping'
    
    check_vectorwarp_extra_nodes(vw, tree, ref_tree)

    if vw.type in layer_node_bl_idnames:
        node_type = layer_node_bl_idnames[vw.type]
    elif vw.type == 'MAPPING':
        node_type = 'ShaderNodeMapping'
    elif vw.type == 'BLUR':
        node_type = 'ShaderNodeGroup'

    if ref_tree:
        node_ref = ref_tree.nodes.get(vw.node)
        if node_ref: ref_tree.nodes.remove(node_ref)
        current_node = new_node(tree, vw, 'node', node_type)
        dirty = True
    else:
        current_node, dirty = check_new_node(tree, vw, 'node', node_type, '', True)

    if dirty:
        match vw.type:
            case 'BLUR':
                current_node.node_tree = get_node_tree_lib(lib.BLUR_VECTOR)

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

        m1 = re.match(r'^yp\.layers\[(\d+)\]$', context.parent.path_from_id())
        m2 = re.match(r'^yp\.layers\[(\d+)\]\.masks\[(\d+)\]$', context.parent.path_from_id())
        
        if m1: layer = yp.layers[int(m1.group(1))]
        elif m2: layer = yp.layers[int(m2.group(1))]
        else: layer = None
    
        new_warp = parent.warps.add()

        name = [mt[1] for mt in warp_type_items if mt[0] == self.type][0]

        new_warp.name = get_unique_name(name, parent.warps)
        new_warp.type = self.type
        new_warp.blend_type = 'ADD'

        if layer:
            new_warp.texcoord_type = layer.texcoord_type
            new_warp.uv_name = layer.uv_name

        if self.type in {'MAPPING', 'BLUR'}:
            new_warp.blend_type = 'MIX'

        check_vectorwarp_trees(parent)

        if m1:
            context.layer_ui.expand_vector = True
        elif m2:
            context.layer_ui.masks[int(m2.group(2))].expand_vector = True

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
        node = get_active_ypaint_node()
        group_tree = node.node_tree
        yp = group_tree.yp

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

        tree = get_vw_tree(layer)

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

        check_vectorwarp_trees(layer)

        # # Rearrange nodes
        if layer:
            rearrange_layer_nodes(layer)
            reconnect_layer_nodes(layer)
        else: 
            rearrange_yp_nodes(group_tree)
            reconnect_yp_nodes(group_tree)

        # Update UI
        context.window_manager.ypui.need_update = True

        return {'FINISHED'}
    

def generate_image_warp_node(parent, layer, layer_ui, image_name):
    new_warp = parent.warps.add()

    type = 'IMAGE'

    name = [mt[1] for mt in warp_type_items if mt[0] == type][0]

    new_warp.name = get_unique_name(name, parent.warps)
    new_warp.type = type
    new_warp.blend_type = 'ADD'
    new_warp.image_name = image_name

    check_vectorwarp_trees(parent)

    m1 = re.match(r'^yp\.layers\[(\d+)\]$', parent.path_from_id())
    m2 = re.match(r'^yp\.layers\[(\d+)\]\.masks\[(\d+)\]$', parent.path_from_id())
    if m1:
        layer_ui.expand_vector = True
    elif m2:
        layer_ui.masks[int(m2.group(2))].expand_vector = True

    # Reconnect and rearrange nodes
    reconnect_layer_nodes(layer)
    rearrange_layer_nodes(layer)



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

    image_name : StringProperty(name="Image")
    image_coll : CollectionProperty(type=bpy.types.PropertyGroup)
    
    @classmethod
    def poll(cls, context):
        return get_active_ypaint_node() 

    def invoke(self, context, event):
        obj = context.object
        node = get_active_ypaint_node()
        yp = node.node_tree.yp

        self.parent = context.parent
        self.layer = context.layer if hasattr(context, 'layer') else None
        self.layer_ui = context.layer_ui if hasattr(context, 'layer_ui') else None

        self.image_coll.clear()
        imgs = bpy.data.images
        baked_channel_images = get_all_baked_channel_images(node.node_tree)
        for img in imgs:
            if is_image_available_to_open(img) and img not in baked_channel_images:
                self.image_coll.add().name = img.name
        
        return context.window_manager.invoke_props_dialog(self)

    # def check(self, context):
    #     return True

    def draw(self, context):
        # node = get_active_ypaint_node()
        # yp = node.node_tree.yp
        # obj = context.object
        self.layout.prop_search(self, "image_name", self, "image_coll", icon='IMAGE_DATA')
        # row = self.layout.row()

        # col = row.column()
        # col.label(text='Interpolation:')

        # col = row.column()
        # col.prop(self, 'interpolation', text='')
        
        # print("has parent draw =", hasattr(context, 'parent'))


    def execute(self, context):
        T = time.time()

        node = get_active_ypaint_node()

        wm = context.window_manager

        if self.image_name == '':
            self.report({'ERROR'}, "No image selected!")
            return {'CANCELLED'}

        generate_image_warp_node(self.parent, self.layer, self.layer_ui, self.image_name)
        # Update UI
        wm.ypui.need_update = True
        print('INFO: Image', self.image_name, 'is opened in', '{:0.2f}'.format((time.time() - T) * 1000), 'ms!')
        wm.yptimer.time = str(time.time())

        return {'FINISHED'}

class YOpenImageToVectorWarp(bpy.types.Operator):
    """Open Image to Vector Warp"""
    bl_idname = "wm.y_open_image_to_vector_warp"
    bl_label = "Open Image"
    bl_options = {'REGISTER', 'UNDO'}

    # interpolation : EnumProperty(
    #     name = 'Image Interpolation Type',
    #     description = 'Image interpolation type',
    #     items = interpolation_type_items,
    #     default = 'Linear'
    # )

    # file_browser_filepath : StringProperty(default='')
    filepath: StringProperty(subtype='FILE_PATH', options={'SKIP_SAVE'})

    filter_folder : BoolProperty(default=True, options={'HIDDEN', 'SKIP_SAVE'})
    filter_image : BoolProperty(default=True, options={'HIDDEN', 'SKIP_SAVE'})

    relative : BoolProperty(name="Relative Path", default=True, description="Apply relative paths")

    use_udim_detecting : BoolProperty(
        name = 'Detect UDIMs',
        description = 'Detect selected UDIM files and load all matching tiles.',
        default = True
    )
    
    @classmethod
    def poll(cls, context):
        return get_active_ypaint_node() 

    def invoke(self, context, event):
        # obj = context.object
        # node = get_active_ypaint_node()
        # yp = self.yp = node.node_tree.yp
        # if self.file_browser_filepath != '':
        #     if get_user_preferences().skip_property_popups and not event.shift:
        #         return self.execute(context)
        #     return context.window_manager.invoke_props_dialog(self)
        self.parent = context.parent
        self.layer = context.layer if hasattr(context, 'layer') else None
        self.layer_ui = context.layer_ui if hasattr(context, 'layer_ui') else None

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    # def check(self, context):
    #     return True

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'relative')
        if UDIM.is_udim_supported():
            layout.prop(self, 'use_udim_detecting')


    def execute(self, context):

        print("filepath=", self.filepath)

        T = time.time()

        directory = os.path.dirname(self.filepath)

        # todo : reuse sama method

        if not UDIM.is_udim_supported():
            image = load_image(self.filepath, directory)
        else:
            ori_ui_type = bpy.context.area.type
            bpy.context.area.type = 'IMAGE_EDITOR'
           
            bpy.ops.image.open(
                filepath=self.filepath, directory=directory, 
                relative_path=self.relative, 
                use_udim_detecting=self.use_udim_detecting
            )
            image = bpy.context.space_data.image
            bpy.context.area.type = ori_ui_type

        if image:
            self.image_name = image.name

        if self.image_name == '':
            self.report({'ERROR'}, "No image selected!")
            return {'CANCELLED'}
        
        node = get_active_ypaint_node()

        wm = context.window_manager

        generate_image_warp_node(self.parent, self.layer, self.layer_ui, self.image_name)

        # Update UI
        wm.ypui.need_update = True

        print('INFO: Image', self.image_name, 'is opened in', '{:0.2f}'.format((time.time() - T) * 1000), 'ms!')
        wm.yptimer.time = str(time.time())

        return {'FINISHED'}

def update_new_uv_map(self, context):
    if not UDIM.is_udim_supported(): return

    if get_user_preferences().enable_auto_udim_detection:
        mat = get_active_material()
        objs = get_all_objects_with_same_materials(mat)
        self.use_udim = UDIM.is_uvmap_udim(objs, self.uv_map)

class YNewImageToVectorWarp(bpy.types.Operator):
    """New Image to Vector Warp"""
    bl_idname = "wm.y_new_image_to_vector_warp"
    bl_label = "New Image"
    bl_options = {'REGISTER', 'UNDO'}

    name : StringProperty(default='')

    # For image layer
    width : IntProperty(name='Width', default=1024, min=1, max=16384)
    height : IntProperty(name='Height', default=1024, min=1, max=16384)
    #color : FloatVectorProperty(name='Color', size=4, subtype='COLOR', default=(0.0,0.0,0.0,0.0), min=0.0, max=1.0)
    #alpha : BoolProperty(name='Alpha', default=True)
    hdr : BoolProperty(name='32 bit Float', default=False)

    image_resolution : EnumProperty(
        name = 'Image Resolution',
        items = image_resolution_items,
        default = '1024'
    )

    use_custom_resolution : BoolProperty(
        name= 'Custom Resolution',
        description = 'Use custom Resolution to adjust the width and height individually',
        default = False
    )

    use_udim : BoolProperty(
        name = 'Use UDIM Tiles',
        description = 'Use UDIM Tiles',
        default = False
    )

    uv_map : StringProperty(default='', update=update_new_uv_map)
    uv_map_coll : CollectionProperty(type=bpy.types.PropertyGroup)


    @classmethod
    def poll(cls, context):
        return get_active_ypaint_node()

    def invoke(self, context, event):
        ypup = get_user_preferences()
        obj = context.object
        node = get_active_ypaint_node()

        yp = self.yp = node.node_tree.yp

        self.parent = context.parent
        self.layer = context.layer if hasattr(context, 'layer') else None
        self.layer_ui = context.layer_ui if hasattr(context, 'layer_ui') else None

        name = obj.active_material.name
        items = bpy.data.images

        # Use user preference default image size
        if ypup.default_image_resolution == 'CUSTOM':
            self.use_custom_resolution = True
            self.width = self.height = ypup.default_new_image_size
        elif ypup.default_image_resolution != 'DEFAULT':
            self.image_resolution = ypup.default_image_resolution

        # Layer name
        self.name = get_unique_name(name, items)

        if obj.type == 'MESH':
            uv_name = get_default_uv_name(obj, yp)
            self.uv_map = uv_name

            # UV Map collections update
            self.uv_map_coll.clear()
            for uv in get_uv_layers(obj):
                if not uv.name.startswith(TEMP_UV):
                    self.uv_map_coll.add().name = uv.name

        if get_user_preferences().skip_property_popups and not event.shift:
            return self.execute(context)
        return context.window_manager.invoke_props_dialog(self, width=320)
    
    def check(self, context):
        ypup = get_user_preferences()

        if not self.use_custom_resolution:
            self.width = int(self.image_resolution)
            self.height = int(self.image_resolution)

        return True
    
    def draw(self, context):
        #yp = self.group_node.node_tree.yp
        node = get_active_ypaint_node()
        yp = node.node_tree.yp
        obj = context.object


        row = split_layout(self.layout, 0.4)
        col = row.column(align=False)
        
        col.label(text='Name:')

        if self.use_custom_resolution == False:
            col.label(text='')
            col.label(text='Resolution:')
        elif self.use_custom_resolution == True:
            col.label(text='')
            col.label(text='Width:')
            col.label(text='Height:')

        col = row.column(align=False)

        col.prop(self, 'name', text='')

        if self.use_custom_resolution == False:
            crow = col.row(align=True)
            crow.prop(self, 'use_custom_resolution')
            crow = col.row(align=True)
            crow.prop(self, 'image_resolution', expand= True,)
        elif self.use_custom_resolution == True:
            crow = col.row(align=True)
            crow.prop(self, 'use_custom_resolution')
            col.prop(self, 'width', text='')
            col.prop(self, 'height', text='')

        col.prop(self, 'hdr')

        # crow = col.row(align=True)
        # crow.prop_search(self, "uv_map", self, "uv_map_coll", text='', icon='GROUP_UVS')

        # if UDIM.is_udim_supported():
        #     col.prop(self, 'use_udim')

    def execute(self, context):
        T = time.time()

        node = get_active_ypaint_node()
        yp = node.node_tree.yp

        same_name = [i for i in bpy.data.images if i.name == self.name]

        if same_name:
            self.report({'ERROR'}, "Image named '" + self.name +"' is already available!")
            return {'CANCELLED'}
        
        if self.name == '':
            self.report({'ERROR'}, "Name cannot be empty!")
            return {'CANCELLED'}

        img = None

        alpha = True
        color = (0.5, 0.5, 0.5, 1.0)
        
        obj = context.object
        mat = obj.active_material

        if self.use_udim:
            objs = get_all_objects_with_same_materials(mat)
            tilenums = UDIM.get_tile_numbers(objs, self.uv_map)

        if self.use_udim:
            img = bpy.data.images.new(
                name=self.name, width=self.width, height=self.height, 
                alpha=alpha, float_buffer=self.hdr, tiled=True
            )

            # Fill tiles
            for tilenum in tilenums:
                UDIM.fill_tile(img, tilenum, color, self.width, self.height)
            UDIM.initial_pack_udim(img, color)

        else:
            img = bpy.data.images.new(
                name=self.name, width=self.width, height=self.height, 
                alpha=alpha, float_buffer=self.hdr
            )

            #img.generated_type = self.generated_type
            img.generated_type = 'BLANK'
            img.generated_color = color
            img.colorspace_settings.name = get_noncolor_name()
            if hasattr(img, 'use_alpha'):
                img.use_alpha = True


        update_image_editor_image(context, img)

        generate_image_warp_node(self.parent, self.layer, self.layer_ui, self.name)

        wm = context.window_manager

        # Update UI
        wm.ypui.need_update = True
        print('INFO: Image', self.name, 'is opened in', '{:0.2f}'.format((time.time() - T) * 1000), 'ms!')
        wm.yptimer.time = str(time.time())

        return {'FINISHED'}
    
def get_cache_name(type):
    name = 'cache_' + type.lower()
    return name

def replace_vector_warp_type(context, vw, new_type, item_name=''):

    yp = vw.id_data.yp
    node = get_active_ypaint_node()
    group_tree = node.node_tree

    # Current source
    tree = get_vw_tree(vw)
    source = tree.nodes.get(vw.node)

    print("replace vector warp type", vw.name, "from", vw.type, "to", new_type)
    # Save source to cache
    existing = None
    for c in vw.cache_nodes:
        if c.type == vw.type:
            existing = c
            print("has existing cache node", existing.name)
            break
    
    if not existing:
        print("no existing cache node", vw.node)
        existing = vw.cache_nodes.add()
        existing.type = vw.type
        existing.name = vw.node
    
    # Remove uv input link
    if any(source.inputs) and any(source.inputs[0].links):
        tree.links.remove(source.inputs[0].links[0])
    
    vw.type = new_type
    vw.node = ''

    # check cache
    for c in vw.cache_nodes:
        if c.type == vw.type:
            vw.node = c.name

    parent = context.parent

    m1 = re.match(r'^yp\.layers\[(\d+)\]$', parent.path_from_id())
    m2 = re.match(r'^yp\.layers\[(\d+)\]\.masks\[(\d+)\]$', parent.path_from_id())
    
    if m1: layer = yp.layers[int(m1.group(1))]
    elif m2: layer = yp.layers[int(m2.group(1))]
    else: layer = None

    check_vectorwarp_trees(parent)

    if m1:
        context.layer_ui.expand_vector = True
    elif m2:
        context.layer_ui.masks[int(m2.group(2))].expand_vector = True

    if layer:
        reconnect_layer_nodes(layer)
        rearrange_layer_nodes(layer)
    else: 
        reconnect_yp_nodes(group_tree)
        rearrange_yp_nodes(group_tree)
        
    # Update UI
    bpy.context.window_manager.ypui.need_update = True

class YReplaceVectorWarpType(bpy.types.Operator):
    bl_idname = "wm.y_replace_vector_warp_type"
    bl_label = "Replace Vector Warp Type"
    bl_description = "Replace Vector Warp Type"
    bl_options = {'REGISTER', 'UNDO'}

    type : EnumProperty(
        name = 'Layer Type',
        items = warp_type_items,
        default = 'IMAGE'
    )

    item_name : StringProperty(name="Item")
    item_coll : CollectionProperty(type=bpy.types.PropertyGroup)

    load_item : BoolProperty(default=False)

    @classmethod
    def poll(cls, context):
        group_node = get_active_ypaint_node()
        return context.object and group_node and len(group_node.node_tree.yp.layers) > 0

    def invoke(self, context, event):
        if self.load_item and self.type in {'IMAGE'}:

            self.item_coll.clear()
            self.item_name = ''

            # Update image names
            if self.type == 'IMAGE':
                baked_channel_images = get_all_baked_channel_images(self.layer.id_data)
                for img in bpy.data.images:
                    if not img.yia.is_image_atlas and not img.yua.is_udim_atlas and img not in baked_channel_images:
                        self.item_coll.add().name = img.name

            return context.window_manager.invoke_props_dialog(self)

        return self.execute(context)

    def draw(self, context):
        layout = self.layout

        split = split_layout(layout, 0.35, align=True)

        #row = self.layout.row()
        if self.type == 'IMAGE':
            split.label(text='Image:')
            split.prop_search(self, "item_name", self, "item_coll", text='', icon='IMAGE_DATA')

    def execute(self, context):

        T = time.time()

        wm = context.window_manager

        vw = context.vector_warp

        if self.type == vw.type and self.type not in {'IMAGE'}: 
            return {'CANCELLED'}

        if self.load_item and self.type in {'IMAGE'} and self.item_name == '':
            self.report({'ERROR'}, "Form is cannot be empty!")
            return {'CANCELLED'}

        replace_vector_warp_type(context, vw, self.type, self.item_name)

        print('INFO: Vector Warp', vw.name, 'is updated in', '{:0.2f}'.format((time.time() - T) * 1000), 'ms!')
        wm.yptimer.time = str(time.time())

        return {'FINISHED'}
    
classes = (
    YVectorWarpCache,
    YVectorWarp,
    YNewVectorWarp,
    YMoveYPaintVectorWarp,
    YRemoveYPaintVectorWarp,
    YOpenAvailableImageToVectorWarp,
    YOpenImageToVectorWarp,
    YNewImageToVectorWarp,
    YReplaceVectorWarpType,
)
         
def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)