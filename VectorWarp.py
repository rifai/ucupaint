import bpy
from .common import *
from bpy.props import *

class YVectorWarp(bpy.types.PropertyGroup):
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
    )


class YNewVectorWarp(bpy.types.Operator):
    bl_idname = "wm.y_new_vector_warp"
    bl_label = "New " + get_addon_title() + " Vector Warp"
    bl_description = "New " + get_addon_title() + " Vector Warp"
    bl_options = {'REGISTER', 'UNDO'}

    type : EnumProperty(
        name = 'Vector Warp Type',
        items = warp_type_items,
        default = 'MAPPING',
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

        new_warp = parent.warps.add()
        # m1 = re.match(r'^yp\.layers\[(\d+)\]$', context.parent.path_from_id())
        # m2 = re.match(r'^yp\.layers\[(\d+)\]\.channels\[(\d+)\]$', context.parent.path_from_id())
        # m3 = re.match(r'^yp\.channels\[(\d+)\]$', context.parent.path_from_id())

        # if m1: layer = yp.layers[int(m1.group(1))]
        # elif m2: layer = yp.layers[int(m2.group(1))]
        # else: layer = None

        # mod = add_new_modifier(context.parent, self.type)

        # #if self.type == 'RGB_TO_INTENSITY' and root_ch.type == 'RGB':
        # #    mod.rgb2i_col = (1,0,1,1)

        # # If RGB to intensity is added, bump base is better be 0.0
        # if layer and self.type == 'RGB_TO_INTENSITY':
        #     for i, ch in enumerate(yp.channels):
        #         c = context.layer.channels[i]
        #         if ch.type == 'NORMAL':
        #             c.bump_base_value = 0.0

        # # Expand channel content to see added modifier
        # if m1:
        #     context.layer_ui.expand_content = True
        # elif m2:
        #     context.layer_ui.channels[int(m2.group(2))].expand_content = True
        # elif m3:
        #     context.channel_ui.expand_content = True

        # # Reconnect and rearrange nodes
        # if layer:
        #     reconnect_layer_nodes(layer)
        #     rearrange_layer_nodes(layer)
        # else: 
        #     reconnect_yp_nodes(group_tree)
        #     rearrange_yp_nodes(group_tree)

        # Update UI
        context.window_manager.ypui.need_update = True

        return {'FINISHED'}

def draw_vector_warp_properties(context, channel_type, nodes, vectorWarp, layout, is_layer_ch=False):

    pass
         
def register():
    bpy.utils.register_class(YVectorWarp)
    bpy.utils.register_class(YNewVectorWarp)


def unregister():
    bpy.utils.unregister_class(YVectorWarp)
    bpy.utils.unregister_class(YNewVectorWarp)