
import bpy, threading, os

from bpy.types import Operator
from bpy.props import StringProperty, IntProperty, BoolProperty

from .. import Layer
from ..common import * 

from .downloader import download_stream, get_thread_id, get_thread
from .downloader import threads

from .properties import assets_lib, TexLibProps, DownloadQueue,  get_textures_dir, cancel_searching

class TexLibAddToUcupaint(Operator, Layer.BaseMultipleImagesLayer):
    """Open Multiple Textures to Layer Ucupaint"""

    bl_label = ""
    bl_idname = "texlib.add_to_ucupaint"

    attribute:StringProperty()
    id:StringProperty()
   
    @classmethod
    def poll(cls, context):
        return get_active_ypaint_node()

    def invoke(self, context, event):
        self.invoke_operator(context)
        return context.window_manager.invoke_props_dialog(self, width=320)
    
    def check(self, context):
        return self.check_operator(context)

    def draw(self, context):
        self.draw_operator(context)
    
    def execute(self, context):
        lib = assets_lib[self.id]
        attr_dwn = lib["downloads"][self.attribute]
        directory = attr_dwn["location"]
        import_list = os.listdir(directory)

        if not self.open_images_to_single_layer(context, directory, import_list):
            return {'CANCELLED'}

        return {'FINISHED'}

class TexLibCancelDownload(Operator):
    """Cancel downloading textures"""

    bl_label = ""
    bl_idname = "texlib.cancel"
    attribute:StringProperty()
    id:StringProperty()

    def execute(self, context:bpy.context):
        thread_id = get_thread_id(self.id, self.attribute)
        thread = get_thread(thread_id)

        if thread == None:
            return {'CANCELLED'}
        thread.cancel = True

        texlib:TexLibProps = context.scene.texlib
        dwn:DownloadQueue
        for dwn in texlib.downloads:
            if dwn.asset_id ==  self.id and dwn.asset_attribute == self.attribute:
                dwn.alive = False
                return {'FINISHED'}
            
        return {'CANCELLED'}

class TexLibRemoveTextureAttribute(Operator):
    """Remove existing textures"""

    bl_label = ""
    bl_idname = "texlib.remove_attribute"
    attribute:StringProperty()
    id:StringProperty()

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.label(text="Are you sure to remove this texture?")
 
    def execute(self, context:bpy.context):
        dir_up = get_textures_dir() + self.id
        dir = dir_up + os.sep + self.attribute
        # print("item", self.id," | attr", self.attribute, " | file ", dir)
        # remove folder
        if os.path.exists(dir):
            for root, dirs, files in os.walk(dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(dir)

            # remove parent folder if empty
            if not os.listdir(dir_up):
                os.rmdir(dir_up)
                my_list = context.scene.texlib.downloaded_material_items
                my_list.remove(my_list.find(self.id))
            return {'FINISHED'}
        return {'CANCELLED'}
    
class TexLibDownload(Operator):
    """Download textures from source"""

    bl_label = ""
    bl_idname = "texlib.download"
    
    attribute:StringProperty()
    id:StringProperty()
    file_size:IntProperty
    file_exist:BoolProperty(default=False)

    def invoke(self, context, event):
        if self.file_exist:
            return context.window_manager.invoke_props_dialog(self)
        return self.execute(context)
    
    def draw(self, context:bpy.context):
        layout = self.layout

        layout.label(text="Already downloaded. Overwrite?", icon="QUESTION")

    def execute(self, context):
        lib = assets_lib[self.id]
        attr_dwn = lib["downloads"][self.attribute]
        link = attr_dwn["link"]
        directory = attr_dwn["location"]
        file_name = os.path.join(directory, attr_dwn["fileName"])

        if not os.path.exists(directory):
            # print("make dir "+directory)
            os.makedirs(directory)

        thread_id = get_thread_id(self.id, self.attribute)
        new_thread = threading.Thread(target=download_stream, args=(link,file_name,thread_id,))
        new_thread.progress = 0
        new_thread.cancel = False
        threads[get_thread_id(self.id, self.attribute)] = new_thread

        new_thread.start()

        texlib = context.scene.texlib
        new_dwn:DownloadQueue = texlib.downloads.add()
        new_dwn.asset_id = self.id
        new_dwn.file_path = file_name
        new_dwn.asset_attribute = self.attribute
        new_dwn.alive = True
        new_dwn.file_size = attr_dwn["size"]
        new_dwn.progress = 0

        return {'FINISHED'}

class TexLibCancelSearch(Operator):
    bl_idname = "texlib.cancel_search"
    bl_label = ""
    
    def execute(self, context):
        cancel_searching(context)
        return{'FINISHED'}
    
class TexLibRemoveTextureAllAttributes(Operator):
    bl_idname = "texlib.remove_attributes"
    bl_label = ""
    id:StringProperty()

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.label(text="Are you sure to remove this textures?")
 
    def execute(self, context:bpy.context):
        dir = get_textures_dir() + self.id 
        print("item", self.id, " | file ", dir)
        my_list = context.scene.texlib.downloaded_material_items
        my_list.remove(my_list.find(self.id))
        # remove folder
        if os.path.exists(dir):
            for root, dirs, files in os.walk(dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(dir)
            return {'FINISHED'}
        
        return {'CANCELLED'}


classes = [
    TexLibAddToUcupaint,
	TexLibCancelDownload,
	TexLibRemoveTextureAttribute,
	TexLibDownload,
	TexLibCancelSearch,
	TexLibRemoveTextureAllAttributes
]

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
        
def unregister():
	for cls in classes:
		bpy.utils.unregister_class(cls)