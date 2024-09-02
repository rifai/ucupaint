
if "bpy" not in locals():
	from . import exporter
else:
    import importlib

    importlib.reload(exporter)

def register():
    exporter.register()

def unregister():
    exporter.unregister()

if __name__ == "__main__":
    register()