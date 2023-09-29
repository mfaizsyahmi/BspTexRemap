import dearpygui.dearpygui as dpg
import DearPyGui_DragAndDrop as dpg_dnd

import logging
from collections import namedtuple
from pathlib import Path

from bsptexremap.common import parse_arguments, setup_logger
from bsptexremap.enums import MaterialEnum as ME
from bsptexremap.materials import MaterialSet # matchars

from bsptexremap.dpg import mappings, gui_utils, colors
from bsptexremap.dpg.modelcontroller import App

BindingType = mappings.BindingType # puts it onto the main scope
_BT = mappings.BindingType # shorthand
_prop = namedtuple("PropertyBinding",["obj","prop"])

def _help(message):
    return gui_utils.add_help_in_place(message)
def _sort_table(sender, sort_specs):
    return gui_utils.sort_table(sender, sort_specs)
def _bind_last_item(app,*args,**kwargs):
    return app.view.bind(dpg.last_item(),*args,**kwargs)

def _filedlg_cb(fn): 
    ''' for feeding the action fn that accepts a path as the first argument
        intended to back-feed the caller fn i.e. same_fn -> dlg -> same_fn
    '''
    cb = lambda sender, app_data: fn(app_data["file_path_name"])
    return cb

def _bare_cb(fn):
    ''' discards the sender,app_data,user_data trio from callback '''
    cb = lambda sender, app_data: fn()
    return cb
    

def setup_fonts():
    return # nah...
    font_path = __file__ + "/../assets/fonts/FiraCode-VariableFont_wght.ttf"
    # add a font registry
    with dpg.font_registry():
        # first argument ids the path to the .ttf or .otf file
        default_font = dpg.add_font(font_path, 18)
    return default_font
    
    
def add_file_dialogs(app):
    file_dlg_cfg = {
        BindingType.BspOpenFileDialog : {
            "tag" : "dlgBspFileOpen",
            "label": "Open BSP file",
            "callback": _filedlg_cb(app.do.open_bsp_file),
            "exts": ("bsp","all")
        },
        BindingType.BspSaveFileDialog : {
            "tag" : "dlgBspFileSaveAs",
            "label": "Save BSP file",
            "callback": _filedlg_cb(app.do.save_bsp_file_as),
            "exts": ("bsp","all")
        },
        BindingType.MatLoadFileDialog : {
            "tag" : "dlgMatFileOpen",
            "label": "Open materials file",
            "callback": _filedlg_cb(app.do.load_mat_file),
            "exts": ("txt","all")
        },
        BindingType.MatExportFileDialog : {
            "tag" : "dlgMatFileExport",
            "label": "Export custom materials file",
            "callback": _filedlg_cb(app.do.export_custommat),
            "exts": ("txt","all")
        }
    }
    for type, item in file_dlg_cfg.items():
        app.view.bind(gui_utils.create_file_dialog(**item), type)


def add_materials_pane(app):
    ### materials pane ###
    _bind = lambda *args,**kwargs: _bind_last_item(app,*args,**kwargs) # shorthand

    with dpg.child_window(border=False):
        dpg.bind_item_theme(dpg.last_item(),"theme:normal_table")

        matpath_box = dpg.add_input_text(label="path",readonly=True)
        _bind(_BT.Value,_prop(app.data,"matpath"))
        with dpg.tooltip(matpath_box):
            dpg.add_text("")
            _bind(_BT.FormatValue,_prop(app.data,"matpath"),
                  ["{}",lambda val:val])

        dpg.add_button(label="Load...",callback=_bare_cb(app.do.load_mat_file))

        with dpg.collapsing_header(label="Summary",default_open=True):

            ## Material summary table
            ## X | Material | Total | Usable | Assigned
            dpg.add_table(resizable=True)
            _bind(_BT.MaterialSummaryTable)

        with dpg.collapsing_header(label="Entries"):

            ## Material type fiter
            dpg.add_input_text(label="filter type",
                               hint=f"Material chars e.g. {MaterialSet.MATCHARS}")
            _bind(_BT.Value,_prop(app.view,"filter_matchars"))

            ## material name filter
            dpg.add_input_text(label="filter name",hint=f"Material name")
            _bind(_BT.Value,_prop(app.view,"filter_matnames"))

            ## Material entries table
            ## Mat | Name | Usable
            dpg.add_table(resizable=True,sortable=True,callback=_sort_table)
            _bind(_BT.MaterialEntriesTable)

        with dpg.collapsing_header(label="Remaps",default_open=True):

            with dpg.table(header_row=False):
                for i in range(2): dpg.add_table_column()

                with dpg.table_row():

                    dpg.add_checkbox(label="grouped")
                    _bind(_BT.Value,_prop(app.view,"texremap_grouped"))

                    dpg.add_checkbox(label="hide empty")
                    _bind(_BT.Value,_prop(app.view,"texremap_not_empty"))

                with dpg.table_row():

                    dpg.add_checkbox(label="sort")
                    _bind(_BT.Value,_prop(app.view,"texremap_sort"))

                    dpg.add_checkbox(label="reverse")
                    _bind(_BT.Value,_prop(app.view,"texremap_revsort"))

            dpg.add_separator()

            ## Texture remap list
            dpg.add_group()
            _bind(_BT.TextureRemapList)

        app.view.render_material_tables()


def add_textures_pane(app):
    ### textures pane ###
    _bind = lambda *args,**kwargs: _bind_last_item(app,*args,**kwargs) # shorthand

    with dpg.child_window(autosize_y=False,menubar=True) as winTextures:
        #dpg.bind_item_theme(dpg.last_item(),"theme:main_window") #"theme:normal_table"

        with dpg.menu_bar():

            with dpg.menu(label="Show:All") as mnuTexShow:
                _bind(_BT.FormatLabel,_prop(app.view,"gallery_show_val"),
                      data=["Show:{:.3s}", mappings.gallery_show])

                ## ( ) Embedded  ( ) External  ( ) All
                dpg.add_radio_button(mappings.gallery_show,horizontal=True)
                _bind(_BT.TextMappedValue,_prop(app.view,"gallery_show_val"),
                      data=mappings.gallery_show )

                dpg.add_separator()

                dpg.add_text("Referenced WAD files")
                _bind(_BT.FormatValue, _prop(app.view,"wadstats"),
                      ["Referenced WAD files: {}",lambda stats:len(stats) ] )

                grpWadlist = dpg.add_group()
                _bind(_BT.WadListGroup)

                def _select_all_wads(value=True):
                    for child in dpg.get_item_children(grpWadlist, 1):
                        dpg.set_value(child,value)

                with dpg.group(horizontal=True):
                    dpg.add_checkbox(label="All",
                                     callback=lambda s,a,u:_select_all_wads(a))
                    dpg.add_button(label="load selected",
                                   callback=app.do.load_selected_wads)

            with dpg.menu(label="Size:Stuff") as mnuTexSize:
                _bind(_BT.FormatLabel,
                      _prop(app.view,"gallery_size_val"),
                      ["Size:{}",
                       lambda _:"{:.2f}x/{}px"\
                                .format(app.view.gallery_size_scale,
                                        app.view.gallery_size_maxlen)]
                )

                ## Mapped scale/maxlen values
                for i, text in enumerate(mappings.gallery_sizes):
                    dpg.add_menu_item(label=text,check=True)
                    _bind(_BT.ValueIs,_prop(app.view,"gallery_size_val"), i)

                ## [--|-------] scale slider
                dpg.add_slider_float(label="scale",max_value=16.0,clamped=True)
                _bind(_BT.Value,_prop(app.view,"gallery_size_scale"))

                ## [-----|----] maxlen slider
                dpg.add_slider_int(label="max len.",max_value=2048,
                                   default_value=512,clamped=True)
                _bind(_BT.Value,_prop(app.view,"gallery_size_maxlen"))

            with dpg.menu(label="Sort:Sure"):
                _bind(_BT.FormatLabel,_prop(app.view,"gallery_sort_val"),
                      ["Sort:{}",
                       lambda val:mappings.gallery_sort_map[val].short])

                ## Mapped sort values
                sep = (5,)
                for i, text in enumerate(mappings.gallery_sortings):
                    if i in sep: dpg.add_separator()
                    dpg.add_menu_item(label=text,check=True)
                    _bind(_BT.ValueIs, _prop(app.view,"gallery_sort_val"), i)

            with dpg.menu(label="Filter:OFF") as mnuFilter:
                _bind(_BT.FormatLabel,_prop(app,"view"),
                      ["Filter:{}",
                       lambda view: "ON" if len(view.filter_str) \
                                         or view.filter_unassigned \
                                         or view.filter_radiosity \
                                         else "OFF"
                      ])

                ## [____________] filter
                dpg.add_input_text(label="filter")
                _bind(_BT.Value,_prop(app.view,"filter_str"))

                ## [ ] Textures without materials only
                dpg.add_checkbox(label="Textures without materials only")
                _bind(_BT.Value,_prop(app.view,"filter_unassigned"))

                ## [ ] Exclude radiosity textures
                dpg.add_checkbox(label="Exclude radiosity textures")
                _bind(_BT.Value,_prop(app.view,"filter_radiosity"))
                _help("These are textures embedded by VHLT+'s RAD to make translucent objects light properly")

            with dpg.menu(label="Selection"):

                dpg.add_menu_item(label="Select all", user_data=True,
                                  callback=app.do.select_all_textures)

                dpg.add_menu_item(label="Select none", user_data=False,
                                  callback=app.do.select_all_textures)

                dpg.add_separator()

                with dpg.menu(label="Set material to"):

                    for mat in app.data.matchars:
                        dpg.add_menu_item(
                                label=f"{ME(mat).value} - {ME(mat).name}",
                                user_data = mat,
                                callback=app.do.selection_set_material
                        )

                dpg.add_menu_item(label="Embed into BSP",
                                  user_data=True,
                                  callback=app.do.selection_embed)

                dpg.add_menu_item(label="Unembed from BSP",
                                  user_data=False,
                                  callback=app.do.selection_embed)

            dpg.add_menu_item(label="Refresh", tag="gallery refresh",
                              callback=lambda s,a,u:app.view.gallery.render())

        #with dpg.group() as gallery_root:
        with dpg.child_window(border=False,horizontal_scrollbar=True) as gallery_root:
            app.view.bind( gallery_root, _BT.GalleryRoot )

    def _center_resize(sender):
        app.view.gallery.reflow() # reflow the gallery view

    with dpg.item_handler_registry() as resize_handler:
        dpg.add_item_resize_handler(callback=_center_resize)

    app.view.gallery.submit(gallery_root)
    #dpg.bind_item_handler_registry(winTextures, resize_handler)
    dpg.bind_item_handler_registry("Primary Window", resize_handler)


def add_right_pane(app):
    ### options/actions pane ###
    _bind = lambda *args,**kwargs: _bind_last_item(app,*args,**kwargs) # shorthand

    with dpg.child_window(border=False):
        dpg.bind_item_theme(dpg.last_item(),"theme:normal_table")

        dpg.add_text("On load:")
        dpg.add_checkbox(label="Auto find and load materials")
        _bind(_BT.Value, _prop(app.data,"auto_load_materials"))

        dpg.add_checkbox(label="Auto find and load WADs")
        _bind(_BT.Value, _prop(app.data,"auto_load_wads"))

        dpg.add_checkbox(label="Parse info_texture_remap entity in map")
        _bind(_BT.Value, _prop(app.data,"auto_parse_ents"))
        _help("TODO")

        dpg.add_text("Before save:")
        dpg.add_text("info_texture_remap action:",indent=8)
        _help(f"""
info_texture_remap is an entity that mappers can insert to remap entities.
It is primarily used with the command line version BspTexRemap as part of the
post-compilation step.

Options:
- {mappings.remap_entity_actions[0]}: Inserts this entity, or updates its entries.
If you forgo this step, the texture renamings would be irreversible.
- {mappings.remap_entity_actions[1]}: Removes all instances of this entity.
- {mappings.remap_entity_actions[2]}
        """.strip())

        ## ( ) Insert   ( ) Remove   ( ) Do nothing
        dpg.add_radio_button(mappings.remap_entity_actions,indent=16)
        _bind(_BT.TextMappedValue, _prop(app.data,"remap_entity_action"),
              data=mappings.remap_entity_actions )

        dpg.add_text("")

        dpg.add_button(label="Save BSP", width=128, 
                       callback=lambda:app.do.save_bsp_file(app.data.backup))
        _help("Remaps texture and save in the same file")

        dpg.add_checkbox(label="Backup", indent=8)
        _bind(_BT.Value, _prop(app.data,"backup"))
        _help("Makes backup before saving")

        dpg.add_button(label="Save BSP as...", width=128, 
                       callback=_bare_cb(app.do.save_bsp_file_as))
        _help("Remaps texture and save in another file")

        dpg.add_button(label="Export custom materials", 
                       callback=_bare_cb(app.do.export_custommat))
        _help("Generates custom material file that can be used\nwith BspTexRemap.exe (the console program)")


def add_main_window(app, default_font=None):
    ''' main window layout '''
    _bind = lambda *args,**kwargs: _bind_last_item(app,*args,**kwargs) # shorthand
    _mi = dpg.add_menu_item
    ___ = dpg.add_separator

    with dpg.window(tag="Primary Window",no_scrollbar=True):
        dpg.bind_item_theme(dpg.last_item(),"theme:main_window")

        with dpg.menu_bar() as menubar:

            with dpg.menu(label="BSP"):
            
                _mi(label="Open",    callback=_bare_cb(app.do.open_bsp_file))
                ___() # separtor
                
                _mi(label="Save",    callback=lambda:app.do.save_bsp_file(app.data.backup))
                _mi(label="Save As", callback=_bare_cb(app.do.save_bsp_file_as))
                ___()
                
                _mi(label="Reload",  callback=app.do.reload)
                ___()
                
                _mi(label="Exit",    callback=exit)

            with dpg.menu(label="Materials"):
            
                _mi(label="Load",
                                  callback=_bare_cb(app.do.load_mat_file))
                _mi(label="Export custom materials",
                                  callback=_bare_cb(app.do.export_custommat))
                ___()
                
                _mi(label="Auto-load from BSP path",check=True)
                _bind(_BT.Value, _prop(app.data,"auto_load_materials"))
                ___()
                
                _mi(label="Parse info_texture_remap entity in map")
                _mi(label="Automatically on map load",indent=8,check=True)
                _bind(_BT.Value, _prop(app.data,"auto_parse_ents"))
                

            with dpg.menu(label="Textures"):
                _mi(label="Auto-load WADs from BSP path",check=True)
                _bind(_BT.Value, _prop(app.data,"auto_load_wads"))

            with dpg.menu(label="Tools"):
                _mi(label="Log console",check=True,
                    callback=lambda s,a,u:\
                             dpg.configure_item(gui_utils.DpgLogHandler.TAG,show=a))
                _mi(label="GUI item registry",
                    callback=lambda *_:dpg.show_item_registry())
                _mi(label="GUI style editor",
                    callback=lambda *_:dpg.show_style_editor())
                _mi(label="Show loading",check=True,
                    callback=lambda s,a,u:gui_utils.show_loading(a))

        ### MAIN LAYOUT TABLE ###
        with dpg.table(resizable=True,height=-8) as mainLayoutTable: # header_row=False,
            dpg.bind_item_theme(dpg.last_item(),"theme:layout_table")

            col1 = dpg.add_table_column(label="Materials",width=200)
            _bind(_BT.FormatLabel, _prop(app.data,"mat_set"),
                  ["Materials {}",
                   lambda mat: f"({len(+mat)}/{len(mat)})" \
                   if app.data.matpath else ""])

            col2 = dpg.add_table_column(label="Textures",init_width_or_weight=3)
            _bind(_BT.FormatLabel, _prop(app,"view"),
                  ["Textures {}",lambda view: "({}M + {}X = {}T, {}V)"\
                   .format(len(view.app.data.bsp.textures_m),
                           len(view.app.data.bsp.textures_x),
                           len(view.app.data.bsp.textures),
                           len(view.gallery.data)
                   ) if view.app.data.bsp else "({}T, {}V)"\
                   .format(len(view.textures),len(view.gallery.data))])

            dpg.add_table_column(label="Options/Actions",width=200)

            with dpg.table_row() as mainLayoutRow:

                ### materials pane ###
                add_materials_pane(app)

                ### textures pane ###
                add_textures_pane(app)

                ### options/actions pane ###
                add_right_pane(app)

    # set font of specific widget
    if default_font:
        dpg.bind_font(default_font)
    ### END OF WINDOW LAYOUT


def main():
    dpg.create_context(); dpg_dnd.initialize()

    args = parse_arguments(gui=True)
    setup_logger(args.log) # for console log
    log = logging.getLogger() ## "__main__" should use the root logger
    log.addHandler(gui_utils.DpgLogHandler(0,show=False))

    app = App()
    dpg_dnd.set_drop(app.do.handle_drop)

    default_font = setup_fonts()
    colors.add_themes()
    add_file_dialogs(app)
    add_main_window(app, default_font)
    #app.view.reflect()
    
    if args.bsppath:
        app.data.load_bsp(args.bsppath)

    dpg.create_viewport(title='BspTexRemap GUI', width=1200, height=800)
    dpg.set_viewport_decorated(True)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("Primary Window", True)
    dpg.set_frame_callback(4,callback=app.view.set_viewport_ready)

    dpg.start_dearpygui()
    dpg.destroy_context()

if __name__ == "__main__":
    main()
