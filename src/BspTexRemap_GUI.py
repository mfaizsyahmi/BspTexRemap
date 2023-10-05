import dearpygui.dearpygui as dpg
import DearPyGui_DragAndDrop as dpg_dnd

import logging, sys
from collections import namedtuple
from pathlib import Path

from bsptexremap.common import parse_arguments, setup_logger
from bsptexremap.enums import MaterialEnum as ME
from bsptexremap.materials import MaterialSet # matchars

from bsptexremap.dpg import mappings, gui_utils, colors, consts
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
        BindingType.CustomMatLoadFileDialog : {
            "tag" : "dlgCustomMatFileLoad",
            "label": "Load custom material entries file",
            "callback": _filedlg_cb(app.do.load_custommat_file),
            "exts": ("txt","all")
        },
        BindingType.CustomMatExportFileDialog : {
            "tag" : "dlgCustomMatFileExport",
            "label": "Export custom materials file",
            "callback": _filedlg_cb(app.do.export_custommat),
            "exts": ("txt","all")
        }
    }
    for type, item in file_dlg_cfg.items():
        app.view.bind(gui_utils.create_file_dialog(**item), type)


def add_materials_window(app, tag):
    ### materials pane ###
    _bind = lambda *args,**kwargs: _bind_last_item(app,*args,**kwargs) # shorthand

    with dpg.window(label="Materials", tag=tag, on_close=app.view.update_window_state):

        matpath_box = dpg.add_input_text(label="path",readonly=True)
        _bind(_BT.Value,_prop(app.data,"matpath"))
        with dpg.tooltip(matpath_box,delay=0.5):
            dpg.add_text("")
            _bind(_BT.FormatValue,_prop(app.data,"matpath"),
                  ["{}",lambda val:val])

        dpg.add_button(label="Load...",callback=_bare_cb(app.do.load_mat_file))

        with dpg.collapsing_header(label="Summary",default_open=True):

            ## Material summary table
            ## X | Material | Total | Usable | Assigned
            dpg.add_table(resizable=True) # ,pad_outerX=True
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
            dpg.add_table(resizable=True,sortable=True,
                          callback=_sort_table) # ,pad_outerX=True
            _bind(_BT.MaterialEntriesTable)


def add_wannabe_window(app,tag):
    _bind = lambda *args,**kwargs: _bind_last_item(app,*args,**kwargs) # shorthand

    with dpg.window(label="Remaps", tag=tag, on_close=app.view.update_window_state):

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

        dpg.add_separator()
        with dpg.group(horizontal=True):
            dpg.add_button(label="Import", callback=_bare_cb(app.do.load_mat_file))
            dpg.add_button(label="Export", callback=_bare_cb(app.do.export_custommat))
            dpg.add_button(label="Clear ", callback=_bare_cb(app.do.clear_wannabes))

    app.view.render_material_tables()


def add_textures_window(app, tag):
    ### textures pane ###
    _bind = lambda *args,**kwargs: _bind_last_item(app,*args,**kwargs) # shorthand

    with dpg.window(label="Textures", tag=tag, no_close=True,
                    on_close=app.view.update_window_state) as winTextures:

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
                sep = mappings.gallery_sort_separators
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

                dpg.add_menu_item(label="Select remap entries", user_data=True,
                                  callback=app.do.select_wannabes)
                #with dpg.popup(dpg.last_item()):
                #    dpg.add_Text("Hold Ctrl to unite selection")
                                  
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

            gallery_status = dpg.add_text("")
            _bind(_BT.FormatValue, _prop(app,"view"),
                  ["{}",lambda view: "({}M + {}X = {}T, {}V)"\
                   .format(len(view.app.data.bsp.textures_m),
                           len(view.app.data.bsp.textures_x),
                           len(view.app.data.bsp.textures),
                           len(view.gallery.data)
                   ) if view.app.data.bsp else "({}T, {}V)"\
                   .format(len(view.textures),len(view.gallery.data))])

            with dpg.tooltip(gallery_status,delay=0.5):
                dpg.add_text(consts.GALLERY_STATUS_LEGEND)

        #with dpg.child_window(border=False,horizontal_scrollbar=True) as gallery_root:
        with dpg.group() as gallery_root:
            app.view.bind( gallery_root, _BT.GalleryRoot )

    def _center_resize(sender):
        indent = dpg.get_item_rect_size(winTextures)[0]\
               - dpg.get_item_rect_size(gallery_status)[0] - 16
        if indent <=544: indent=0
        dpg.set_item_indent(gallery_status, indent)
        app.view.gallery.reflow() # reflow the gallery view

    with dpg.item_handler_registry() as resize_handler:
        dpg.add_item_resize_handler(callback=_center_resize)

    app.view.gallery.submit(gallery_root)
    dpg.bind_item_handler_registry(winTextures, resize_handler)


def add_options_window(app,tag):
    ### options/actions pane ###
    _bind = lambda *args,**kwargs: _bind_last_item(app,*args,**kwargs) # shorthand

    with dpg.window(label="Options/Actions", tag=tag,
                    on_close=app.view.update_window_state):

        dpg.add_text("On load:")
        dpg.add_text("Auto find and load:",indent=8)
        dpg.add_checkbox(label="materials.txt",indent=16)
        _bind(_BT.Value, _prop(app.data,"auto_load_materials"))
        _help("Looks for materials.txt")

        dpg.add_checkbox(label="WADs",indent=16)
        _bind(_BT.Value, _prop(app.data,"auto_load_wads"))

        dpg.add_checkbox(label="Custom remaps",indent=16)
        _bind(_BT.Value, _prop(app.data,"auto_load_wannabes"))
        _help(consts.AUTOLOAD_REMAPS_HELP)

        dpg.add_separator()
        dpg.add_text("Editing:")

        dpg.add_checkbox(label="Allow stripping embedded textures")
        _bind(_BT.Value, _prop(app.data,"allow_unembed"))
        _help(consts.ALLOW_UNEMBED_HELP)

        dpg.add_separator()
        dpg.add_text("Before save:")

        dpg.add_text("info_texture_remap action:",indent=8)
        _help(consts.REMAP_ENTITY_ACTION_HELP.format(*mappings.remap_entity_actions))

        ## ( ) Insert   ( ) Remove   ( ) Do nothing
        dpg.add_radio_button(mappings.remap_entity_actions,indent=16)
        _bind(_BT.TextMappedValue, _prop(app.data,"remap_entity_action"),
              data=mappings.remap_entity_actions )

        dpg.add_separator()
        dpg.add_text("Save/Export:")

        dpg.add_button(label="Save BSP", width=128,
                       callback=lambda:app.do.save_bsp_file(app.data.backup))
        _help("Remaps texture and save in the same file")

        dpg.add_checkbox(label="Backup", indent=8)
        _bind(_BT.Value, _prop(app.data,"backup"))
        _help("Makes backup before saving")

        dpg.add_button(label="Save BSP as...", width=128,
                       callback=_bare_cb(app.do.save_bsp_file_as))
        _help("Remaps texture and save in another file")

        dpg.add_checkbox(label="Show edit summary")
        _bind(_BT.Value, _prop(app.data,"show_summary"))
        
        dpg.add_button(label="Export custom materials",
                       callback=_bare_cb(app.do.export_custommat))
        _help("Generates custom material file that can be used\nwith BspTexRemap.exe (the console program)")
        
        dpg.add_separator()
        dpg.add_text(consts.NOTES,wrap=0)


def add_misc_dialogs(app):
    _bind = lambda *args,**kwargs: _bind_last_item(app,*args,**kwargs) # shorthand
    
    with dpg.window(label="Edit summary",show=False) as dlg_save_summary:
        _bind(_BT.SummaryDialog)
        
        dpg.add_group()
        _bind(_BT.SummaryBase)
        
        with dpg.collapsing_header(label="Summary",default_open=True):
            dpg.add_table()
            _bind(_BT.SummaryTable)
        
        with dpg.collapsing_header(label="Details"):
            dpg.add_group()
            _bind(_BT.SummaryDetails)
        
        dpg.add_separator()
        dpg.add_button(label="Close", callback=lambda:dpg.hide_item(dlg_save_summary))


def add_viewport_menu(app):
    ''' main window layout '''
    _bind = lambda *args,**kwargs: _bind_last_item(app,*args,**kwargs) # shorthand
    _mi = dpg.add_menu_item
    ___ = dpg.add_separator

    with dpg.viewport_menu_bar():

        with dpg.menu(label="BSP"):

            _mi(label="Open",    callback=_bare_cb(app.do.open_bsp_file))
            ___() # separator

            _mi(label="Save",    callback=lambda:app.do.save_bsp_file(app.data.backup))
            _mi(label="Save As", callback=_bare_cb(app.do.save_bsp_file_as))
            ___()

            _mi(label="Reload",  callback=app.do.reload)
            ___()

            _mi(label="Exit",    callback=exit)

        with dpg.menu(label="Materials"):

            _mi(label="Load materials.txt",
                              callback=_bare_cb(app.do.load_mat_file))
            _mi(label="Auto-load from BSP path",check=True)
            _bind(_BT.Value, _prop(app.data,"auto_load_materials"))
            ___()
            
            _mi(label="Load custom materials",
                              callback=_bare_cb(app.do.load_custommat_file))
            _mi(label="Export custom materials",
                              callback=_bare_cb(app.do.export_custommat))
            ___()


            _mi(label="Automatically on map load:",check=True)
            _bind(_BT.Value, _prop(app.data,"auto_load_wannabes"))
            _mi(label="Parse info_texture_remap entity in map",indent=8,
                callback=_bare_cb(app.do.parse_remap_entities))
            _mi(label="Load custom material remap file",indent=8,
                callback=_bare_cb(app.do.load_custommat_file))


        with dpg.menu(label="Textures"):
            _mi(label="Auto-load WADs from BSP path",check=True)
            _bind(_BT.Value, _prop(app.data,"auto_load_wads"))

            _mi(label="Allow stripping embedded textures",check=True)
            _bind(_BT.Value, _prop(app.data,"allow_unembed"))

        with dpg.menu(label="View"):
            _cb = app.view.update_window_state
            v_t = _mi(label="Textures",    check=True,callback=_cb,enabled=False)
            v_m = _mi(label="Materials",   check=True,callback=_cb)
            v_r = _mi(label="Remaps",      check=True,callback=_cb)
            v_o = _mi(label="Options",     check=True,callback=_cb)
            v_l = _mi(label="Log messages",check=True,callback=_cb)
            ___()
            _mi(label="Save layout",
                callback=lambda: dpg.save_init_file(consts.LAYOUT_INI_PATH))
        app.view.window_binds[_BT.TexturesWindow]["menu"] = v_t
        app.view.window_binds[_BT.MaterialsWindow]["menu"] = v_m
        app.view.window_binds[_BT.RemapsWindow]["menu"] = v_r
        app.view.window_binds[_BT.OptionsWindow]["menu"] = v_o
        app.view.window_binds[_BT.LogWindow]["menu"] = v_l

        with dpg.menu(label="Debug"):
            _mi(label="GUI item registry",
                callback=lambda *_:dpg.show_item_registry())
            _mi(label="GUI style editor",
                callback=lambda *_:dpg.show_style_editor())
            _mi(label="Show loading",check=True,
                callback=lambda s,a,u:gui_utils.show_loading(a))


def main():
    args = parse_arguments(gui=True)
    setup_logger(args.log) # for console log
    log = logging.getLogger() ## "__main__" should use the root logger

    dpg.create_context()
    # must be called before create_viewport
    dpg.configure_app(docking=True, docking_space=True,
                      init_file=consts.LAYOUT_INI_PATH)

    # generate IDs - the IDs are used by the init file, they must be the
    #                same between sessions
    materials_window = dpg.generate_uuid()
    remaps_window    = dpg.generate_uuid()
    textures_window  = dpg.generate_uuid()
    options_window   = dpg.generate_uuid()
    log_window       = dpg.generate_uuid()

    window_binds = {
        _BT.TexturesWindow : {"window": textures_window},
        _BT.MaterialsWindow: {"window": materials_window},
        _BT.RemapsWindow   : {"window": remaps_window},
        _BT.OptionsWindow  : {"window": options_window},
        _BT.LogWindow      : {"window": log_window},
    }


    colors.add_themes()
    colors.setup_fonts()
    dpg.bind_font(colors.AppFonts.Regular.tag)

    app = App()
    app.view.window_binds = window_binds
    dpg_dnd.initialize()
    dpg_dnd.set_drop(app.do.handle_drop)

    gui_utils.DpgLogHandler.TAG = log_window
    log.addHandler(gui_utils.DpgLogHandler(0,on_close=app.view.update_window_state))
    dpg.bind_item_theme(gui_utils.DpgLogHandler.TAG,colors.AppThemes.LogMessage)

    # setup all the windows
    add_file_dialogs(app)
    add_viewport_menu(app)
    add_materials_window(app,materials_window)
    add_wannabe_window(app,remaps_window)
    add_textures_window(app,textures_window)
    add_options_window(app,options_window)
    add_misc_dialogs(app)

    #app.view.reflect()
    app.view.update_window_state(0,0)

    if args.bsppath:
        app.data.load_bsp(args.bsppath)
    app.view.set_viewport_ready() # this will reschedule itself to run later

    dpg.create_viewport(title=consts.GUI_APPNAME, width=1200, height=800)
    dpg.set_viewport_large_icon(Path(sys.path[0]) / "assets/images/BspTexRemap_64.ico")
    dpg.set_viewport_small_icon(Path(sys.path[0]) / "assets/images/BspTexRemap_64.ico")
    dpg.setup_dearpygui()
    dpg.show_viewport()

    dpg.start_dearpygui() # dpg main loop

    app.save_config()
    dpg.destroy_context()


if __name__ == "__main__":
    main()

