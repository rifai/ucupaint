import bpy

from bpy.types import Panel, UIList

from .. import lib

from .properties import assets_lib
from .properties import TexLibProps, MaterialItem, DownloadQueue

from .operators import TexLibAddToUcupaint, TexLibCancelDownload, TexLibDownload, TexLibRemoveTextureAttribute
from .operators import get_thread, get_thread_id
from .downloader import texture_exist

class TexLibBrowser(Panel):
    bl_label = "Texlib Browser"
    bl_idname = "TEXLIB_PT_Browser"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Ucupaint"
    

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        texlib:TexLibProps = scene.texlib

        # layout.prop(texlib, "mode_asset", expand=True)
        # local_files_mode = texlib.mode_asset == "DOWNLOADED"

        # if local_files_mode:
        #     sel_index = texlib.downloaded_material_index
        #     my_list = texlib.downloaded_material_items
        # else:
        sel_index = texlib.material_index
        my_list = texlib.material_items

        layout.prop(texlib, "input_search")
        source_search = layout.row()
        source_search.prop(texlib, "check_all")
        source_search.prop(texlib, "check_local")
        source_search.prop(texlib, "check_ambiencg")
        source_search.prop(texlib, "check_polyhaven")

        searching_dwn = texlib.searching_download
    
        if searching_dwn.alive:
            prog = searching_dwn.progress

            if prog >= 0:
                row_search = layout.row()

                if prog < 10:
                    row_search.label(text="Searching...")
                else:
                    row_search.prop(searching_dwn, "progress", slider=True, text="Retrieving thumbnails.")
                row_search.operator("texlib.cancel_search", icon="CANCEL")
                    
        # print("list", local_files_mode, ":",sel_index,"/",len(my_list))
        # print("list", local_files_mode, ":",texlib.material_index,"/",len(texlib.material_items)," | ", texlib.downloaded_material_index,"/",len(texlib.downloaded_material_items))
        if len(my_list):

            layout.separator()
            layout.label(text="Textures:")
            col_lay = layout.row()
           
            col_lay.template_list("TEXLIB_UL_Material", "material_list", texlib, "material_items", texlib, "material_index")

            if sel_index < len(my_list):
                sel_mat:MaterialItem = my_list[sel_index]
                mat_id:str = sel_mat.name
                
               

                layout.separator()
                layout.label(text="Preview:")
                prev_box = layout.box()
                selected_mat = prev_box.column(align=True)
                selected_mat.alignment = "CENTER"
                selected_mat.template_icon(icon_value=sel_mat.thumb, scale=5.0)
                selected_mat.label(text=mat_id)
                downloads = assets_lib[mat_id]["downloads"]

                layout.separator()
                layout.label(text="Attributes:")
                for d in downloads:
                    dwn = downloads[d]
                    # row.alignment = "LEFT"
                    ukuran = round(dwn["size"] / 1000000,2)
                    lokasi = dwn["location"]
                    
                    check_exist:bool = texture_exist(mat_id, lokasi)

                    # if local_files_mode and not check_exist:
                    #     continue

                    ui_attr = layout.split(factor=0.7)

                    row = ui_attr.row()

                    row.label(text=d, )
                    # rr.label(text=d, )
                    row.label(text=str(ukuran)+ "MB")

                    thread_id = get_thread_id(mat_id, d)
                    dwn_thread = get_thread(thread_id)

                    btn_row = ui_attr.row()
                    btn_row.alignment = "RIGHT"

                    if dwn_thread != None:
                        btn_row.label(text=str(dwn_thread.progress)+"%")
                        op:TexLibCancelDownload = btn_row.operator("texlib.cancel", icon="X")
                        op.attribute = d
                        op.id = mat_id
                    else:
                        if check_exist:
                            op:TexLibAddToUcupaint = btn_row.operator("texlib.add_to_ucupaint", icon="ADD")
                            op.attribute = d
                            op.id = sel_mat.name

                            op_remove:TexLibRemoveTextureAttribute = btn_row.operator("texlib.remove_attribute", icon="REMOVE")
                            op_remove.attribute = d
                            op_remove.id = sel_mat.name

                        op:TexLibDownload = btn_row.operator("texlib.download", icon="IMPORT")
                        op.attribute = d
                        op.id = sel_mat.name
                        op.file_exist = check_exist

            if len(texlib.downloads):
                layout.separator()
                layout.label(text="Downloads:")
                layout.template_list("TEXLIB_UL_Downloads", "download_list", texlib, "downloads", texlib, "selected_download_item")

class TEXLIB_UL_Downloads(UIList):

    def draw_item(self, context, layout, data, item:DownloadQueue, icon, active_data, active_propname, index):
        """Demo UIList."""
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            if item.alive:
                row.prop(item, "progress", slider=True, text=item.asset_id+" | "+item.asset_attribute)
                op:TexLibCancelDownload = row.operator("texlib.cancel", icon="X")  
                op.attribute = item.asset_attribute
                op.id = item.asset_id
            else:
                row.label(text="cancelling")

class TEXLIB_UL_Material(UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        """Demo UIList."""

        from .properties import previews_collection
         
        item_id = item.name
        if hasattr(previews_collection, "preview_items") and item_id in previews_collection.preview_items:
            thumb = previews_collection.preview_items[item_id][3]
        else:
            thumb = lib.custom_icons["input"].icon_id

        row = layout.row(align=True)
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row.template_icon(icon_value = thumb, scale = 1.0)
            row.label(text=item.name)

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text=item.name, icon_value = thumb)


classes = [
    TexLibBrowser,
    TEXLIB_UL_Material,
    TEXLIB_UL_Downloads
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)