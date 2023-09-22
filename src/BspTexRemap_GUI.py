import dearpygui.dearpygui as dpg
import DearPyGui_DragAndDrop as dpg_dnd
import logging
from pathlib import Path
from jankbsp import BspFileBasic as BspFile
from jankbsp.types import EntityList
from bsptexremap.common import parse_arguments
from bsptexremap.enums import MaterialEnum as ME
from bsptexremap.materials import MaterialSet # matchars
from bsptexremap.dpg.modelcontroller import AppModel
from bsptexremap.dpg.galleryview import GalleryView
from bsptexremap.dpg.textureview import TextureView
from bsptexremap.dpg import gui_utils
from bsptexremap.dpg import mappings

# imported funcs apparently can't be called because they're sunders, 
# so these pass them through
def _help(message): 
    return gui_utils._help(message)
def _sort_table(sender, sort_specs): 
    return gui_utils._sort_table(sender, sort_specs)

dpg.create_context(); dpg_dnd.initialize()
args = parse_arguments(gui=True)
app = AppModel() #dpg)
dpg_dnd.set_drop(app.do_drop)
# needs to be after app is instantiated
def _toggle_prop(sender,app_data,user_data): 
    return gui_utils._toggle_prop(sender,app_data,user_data,app=app)

file_dlg_cfg = [{
    "tag" : "dlgBspFileOpen",
    "label": "Open BSP file",
    "callback": app.do_open_file,
    "exts": ("bsp","all")
}, {
    "tag" : "dlgBspFileSaveAs",
    "label": "Save BSP file",
    "callback": app.do_save_file_as,
    "exts": ("bsp","all")
}, {
    "tag" : "dlgMatFileOpen",
    "label": "Open materials file",
    "callback": app.do_load_mat_file,
    "exts": ("txt","all")
}, {
    "tag" : "dlgMatFileExport",
    "label": "Export custom materials file",
    "callback": app.do_load_mat_file,
    "exts": ("txt","all")
}]
for item in file_dlg_cfg:
    gui_utils.create_file_dialog(**item)

app.insert_bindings()
#app.reflect()

with dpg.window(tag="Primary Window",no_scrollbar=True):
    with dpg.menu_bar():
        with dpg.menu(label="BSP"):
            dpg.add_menu_item(label="Open", callback=app.do_show_open_file)
            dpg.add_separator()
            dpg.add_menu_item(label="Save", callback=app.do_save_file)
            dpg.add_menu_item(label="Save As", callback=app.do_show_save_file_as)
            dpg.add_separator()
            dpg.add_menu_item(label="Reload", callback=app.do_reload)
            
        with dpg.menu(label="Materials"):
            dpg.add_menu_item(label="Load",
                              callback=app.do_show_open_mat_file)
            dpg.add_menu_item(label="Export custom materials", 
                              callback=app.do_export_custommat)
            dpg.add_separator()
            app.togglers.add( dpg.add_menu_item(
                    label="Auto-load from BSP path",
                    check=True,
                    user_data="app:auto_load_materials", # holds the tag of the prop
                    callback=_toggle_prop
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
            with dpg.child_window(border=False):
                dpg.add_input_text(label="path",source="app:matpath",readonly=True)
                dpg.add_button(label="Load...",callback=app.do_show_open_mat_file)
                
                with dpg.collapsing_header(label="Summary",default_open=True):
                    with dpg.table(resizable=True,tag="tblMatSummary"): pass
                    
                with dpg.collapsing_header(label="Entries"):
                    dpg.add_input_text(
                            label="filter type", 
                            source="app:filter_matchars",
                            hint=f"Material chars e.g. {MaterialSet.MATCHARS}",
                            callback=app.update
                    )
                    dpg.add_input_text(
                            label="filter name", 
                            source="app:filter_matnames",
                            hint=f"Material name", 
                            callback=app.update
                    )
                    with dpg.table(resizable=True,
                                   tag="tblMatEntries",
                                   sortable=True, 
                                   callback=_sort_table): pass
                app.render_material_tables()
            
            # textures pane
            with dpg.child_window(autosize_y=False,menubar=True) as winTextures: 
                with dpg.menu_bar():
                    with dpg.menu(label="Show") as mnuTexShow:
                        dpg.add_radio_button(mappings.gallery_show,horizontal=True)
                        dpg.add_separator()
                        with dpg.group(tag="grpWadlist"): pass
                        
                        def _select_all_wads(value=True):
                            for child in dpg.get_item_children("grpWadlist", 1):
                                dpg.set_value(child,value)
                                
                        with dpg.group(horizontal=True):
                            dpg.add_checkbox(label="All",
                                             callback=lambda s,a,u:_select_all_wads(a))
                            dpg.add_button(label="load selected")
                        
                    with dpg.menu(label="Size:Stuff"):
                        dpg.add_combo(mappings.gallery_sizes, 
                                      source="app:gallery_size_text",
                                      callback=app.update)
                    with dpg.menu(label="Filter:ON"):
                        dpg.add_input_text(label="filter")
                        dpg.add_checkbox(label="Textures without materials only")
                    with dpg.menu(label="Selection"):
                        dpg.add_menu_item(label="Select all")
                        dpg.add_menu_item(label="Select none")
                        dpg.add_separator()
                        with dpg.menu(label="Set material to"):
                            for mat in app.matchars:
                                dpg.add_menu_item(label=f"{ME(mat).value} - {ME(mat).name}")
                    
                with dpg.group() as gallery_root: pass

            def _center_resize():
                app.gallery_view.render() # reflow the gallery view
            with dpg.item_handler_registry() as resize_handler:
                dpg.add_item_resize_handler(callback=_center_resize)

            app.gallery_view.submit(gallery_root,winTextures)
            dpg.bind_item_handler_registry("Primary Window", resize_handler)
            
            # options/actions pane
            with dpg.child_window(border=False):
                dpg.add_text("On load:")
                dpg.add_checkbox(label="Auto find and load materials",
                                 source="app:auto_load_materials",
                                 callback=app.update)
                dpg.add_checkbox(label="Auto find and load WADs",
                                 source="app:auto_load_wads",
                                 callback=app.update)
                dpg.add_text("On save:")
                dpg.add_checkbox(label="Insert remap entity",
                                 source="app:insert_remap_entity",
                                 callback=app.update)
                _help("Inserts an info_texture_remap entity that maps the texture\nname changes, otherwise the changes would become irreversible.")
                
                dpg.add_text("")
                
                dpg.add_button(label="Save BSP", callback=app.do_save_file)
                _help("Remaps texture and save in the same file")
                
                dpg.add_checkbox(label="Backup", indent=8, 
                                 source="app:backup", callback=app.update)
                _help("Makes backup before saving")
                
                dpg.add_button(label="Save BSP as...",
                               callback=app.do_show_save_file_as)
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
