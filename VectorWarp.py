import bpy
from .common import *


class YVectorWarp(bpy.types.PropertyGroup):
	name : StringProperty(
        name = 'Warp Name',
        description = 'Warp name',
        default = '',
    )

	type : EnumProperty(
        name = 'Warp Type',
        items = layer_type_items,
        default = 'IMAGE'
    )

	source : StringProperty(default='')

	blend_type : EnumProperty(
        name = 'Blend',
        items = blend_type_items,
    )
