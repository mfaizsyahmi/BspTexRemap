import dearpygui.dearpygui as dpg
import DearPyGui_DragAndDrop as dpg_dnd
from pathlib import Path
from jankbsp import BspFileBasic as BspFile
from jankbsp.types import EntityList
from bsptexremap.common import parse_arguments
from bsptexremap.dpg.modelcontroller import AppModel
from bsptexremap.dpg.galleryview import GalleryView
from bsptexremap.dpg.textureview import TextureView

def _help(message):
    last_item = dpg.last_item()
    group = dpg.add_group(horizontal=True)
    dpg.move_item(last_item, parent=group)
    dpg.capture_next_item(lambda s: dpg.move_item(s, parent=group))
    t = dpg.add_text("(?)", color=[0, 255, 0])
    with dpg.tooltip(t):
        dpg.add_text(message)
        
def print_me(sender, app_data): pass

dpg.create_context(); dpg_dnd.initialize()
args = parse_arguments(gui=True)
app = AppModel(dpg)
dpg_dnd.set_drop(app.do_drop)

def toggle_prop(sender,app_data,user_data):
    app.togglers.add(sender)
    dpg.set_value(user_data, app_data)
    app.update()    

# open BSP file dialog
with dpg.file_dialog(
        label="Open BSP file",
        tag="dlgBspFileOpen", 
        directory_selector=False, 
        show=False, modal=True,
        callback=app.do_open_file, 
        width=700 ,height=400):
    dpg.add_file_extension("BSP files (*.bsp){.bsp}", color=(0, 255, 255, 255))
    dpg.add_file_extension("All files (*.*){.*}")
    
# save BSP as dialog
with dpg.file_dialog(
        label="Save BSP file as",
        tag="dlgBspFileSaveAs", 
        directory_selector=False, 
        show=False, modal=True,
        callback=app.do_save_file_as, 
        width=700 ,height=400):
    dpg.add_file_extension("BSP files (*.bsp){.bsp}", color=(0, 255, 255, 255))
    dpg.add_file_extension("All files (*.*){.*}")
    
# open materials file dialog
with dpg.file_dialog(
        label="Open materials file",
        tag="dlgMatFileOpen", 
        directory_selector=False, 
        show=False, modal=True,
        callback=app.do_load_mat_file, 
        width=700 ,height=400):
    dpg.add_file_extension("Text files (*.txt){.txt}", color=(0, 255, 255, 255))
    dpg.add_file_extension("All files (*.*){.*}")

# export materials file dialog
with dpg.file_dialog(
        label="Export custom materials file",
        tag="dlgMatFileExport", 
        directory_selector=False, 
        show=False, modal=True,
        callback=app.do_load_mat_file, 
        width=700 ,height=400):
    dpg.add_file_extension("Text files (*.txt){.txt}", color=(0, 255, 255, 255))
    dpg.add_file_extension("All files (*.*){.*}")

app.insert_bindings()
#app.reflect()

with dpg.window(tag="Primary Window"):
    with dpg.menu_bar():
        with dpg.menu(label="BSP"):
            dpg.add_menu_item(label="Open", callback=app.do_show_open_file)
            dpg.add_separator()
            dpg.add_menu_item(label="Save", callback=app.do_save_file)
            dpg.add_menu_item(label="Save As", callback=app.do_show_save_file_as)
            dpg.add_separator()
            dpg.add_menu_item(label="Reload", callback=app.do_reload)
            
        with dpg.menu(label="Materials"):
            dpg.add_menu_item(label="Load", callback=app.do_show_open_mat_file)
            dpg.add_menu_item(label="Export custom materials", callback=print_me)
            dpg.add_separator()
            app.togglers.add( dpg.add_menu_item(
                    label="Auto-load from BSP path",
                    check=True,
                    user_data="app:auto_load_materials", # holds the tag of the prop
                    callback=toggle_prop
            ) )
    
    with dpg.table(resizable=True,height=-1): # header_row=False,
        cols = []
        cols.append(dpg.add_table_column(label="Materials",width=200))
        cols.append(dpg.add_table_column(label="Textures",init_width_or_weight=3))
        cols.append(dpg.add_table_column(label="Options/Actions",width=200))
        for col in cols: 
            dpg.bind_item_handler_registry(col, app.gallery_view._handler)
        with dpg.table_row():
            # materials pane
            with dpg.group():
                dpg.add_input_text(label="path",source="app:matpath",readonly=True)
                dpg.add_button(label="Load...",callback=app.do_show_open_mat_file)
                with dpg.collapsing_header(label="Summary",default_open=True):
                    with dpg.table(resizable=True,tag="tblMatSummary"): pass
                    app.render_material_summary()
                with dpg.collapsing_header(label="Entries"):
                    pass
            
            # textures pane
            with dpg.child_window(
                    label="Textures",
                    autosize_x=True,
                    horizontal_scrollbar=True,
                    menubar=True
            ) as winTextures:
                with dpg.menu_bar():
                    with dpg.menu(label="Show"):
                        dpg.add_menu_item(label="Embedded",check=True,callback=print_me)
                        dpg.add_menu_item(label="WADs"    ,check=True,callback=print_me)

                    with dpg.menu(label="Filter"):
                        pass
                with dpg.group() as grpTextures: pass
                app.gallery_view.submit(grpTextures, winTextures)
                dpg.bind_item_handler_registry("Primary Window", app.gallery_view._handler)
            
            # options/actions pane
            with dpg.group():
                dpg.add_checkbox(
                        label="Auto find and load materials",
                        source="app:auto_load_materials",
                        callback=app.update
                )
                dpg.add_checkbox(
                        label="Auto find and load WADs",
                        source="app:auto_load_wads",
                        callback=app.update
                )
                dpg.add_checkbox(
                        label="Insert remap entity",
                        source="app:insert_remap_entity",
                        callback=app.update
                )
                _help("Inserts an info_texture_remap entity that maps the texture name\nchanges, otherwise the changes would become irreversible.")
                
                dpg.add_text("")
                
                dpg.add_button(label="Save BSP", callback=app.do_save_file)
                _help("Remaps texture and save in the same file")
                
                dpg.add_checkbox(
                        label="Backup", indent=8, 
                        source="app:backup", callback=app.update
                )
                _help("Makes backup before saving")
                
                dpg.add_button(label="Save BSP as...",callback=app.do_show_save_file_as)
                _help("Remaps texture and save in another file")
                
                dpg.add_button(
                        label="Export custom materials",
                        callback=app.do_show_save_mat_file
                )
                _help("Generates custom material file that can be used\nwith BspTexRemap.exe (the console program)")

if args.bsppath:
    app.load_bsp(args.bsppath)
dpg.set_frame_callback(1,callback=lambda:app.set_viewport_ready())

dpg.show_item_registry()

dpg.create_viewport(title='BspTexRemap GUI', width=1200, height=800)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window("Primary Window", True)

dpg.start_dearpygui()
dpg.destroy_context()
