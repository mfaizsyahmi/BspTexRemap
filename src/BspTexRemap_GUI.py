import dearpygui.dearpygui as dpg
import DearPyGui_DragAndDrop as dpg_dnd
import DearPyGui_LP as dpg_lp

import logging, sys
from collections import namedtuple
from pathlib import Path
from operator import attrgetter

from bsptexremap.common import parse_arguments, setup_logger, get_base_path
from bsptexremap.enums import MaterialEnum as ME
from bsptexremap.materials import MaterialSet # matchars

from bsptexremap.dpg import mappings, gui_utils, colors, consts
from bsptexremap.dpg.modelcontroller import App, PropertyBinding

BindingType = mappings.BindingType # puts it onto the main scope
_BT = mappings.BindingType # shorthand
#_prop = namedtuple("PropertyBinding",["obj","prop"])
_prop = PropertyBinding

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
        },
        BindingType.ExecutableFileDialog : {
            "tag" : "dlgSelectExecutable",
            "label": "Executable file",
            # callback needs to be set per call
            "callback": _filedlg_cb(lambda:True),
            "exts": ("exe","scripts","all")
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
                _bind(_BT.FormatLabel, _prop(app.view,"gallery_show_val"),
                      data=["Show:{:.3s}", mappings.gallery_show])

                ## ( ) Embedded  ( ) External  ( ) All
                dpg.add_radio_button(mappings.gallery_show,horizontal=True)
                _bind(_BT.TextMappedValue, _prop(app.view,"gallery_show_val"),
                      data=mappings.gallery_show )

                dpg.add_separator()

                dpg.add_text("Referenced WAD files")
                _bind(_BT.FormatValue, _prop(app.view,"wadstats"),
                      ["Referenced WAD files: {}", lambda stats:len(stats) ] )

                grpWadlist = dpg.add_group()
                _bind(_BT.WadListGroup)

                def _select_all_wads(value=True):
                    for child in dpg.get_item_children(grpWadlist, 1):
                        dpg.set_value(child,value)
                    # unfortunately this needs to be done as well
                    for thing in app.view.wadstats:
                        thing.selected = value

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
                    _bind(_BT.ValueIs, _prop(app.view,"gallery_size_val"), i)

                ## [--|-------] scale slider
                dpg.add_slider_float(label="scale",max_value=16.0,clamped=True)
                _bind(_BT.Value, _prop(app.view,"gallery_size_scale"))

                ## [-----|----] maxlen slider
                dpg.add_slider_int(label="max len.",max_value=2048,
                                   default_value=512,clamped=True)
                _bind(_BT.Value, _prop(app.view,"gallery_size_maxlen"))

            with dpg.menu(label="Sort:Sure"):
                _bind(_BT.FormatLabel, _prop(app.view,"gallery_sort_val"),
                      ["Sort:{}",
                       lambda val:mappings.gallery_sort_map[val].short])

                ## Mapped sort values
                sep = mappings.gallery_sort_separators
                for i, text in enumerate(mappings.gallery_sortings):
                    if i in sep: dpg.add_separator()
                    dpg.add_menu_item(label=text,check=True)
                    _bind(_BT.ValueIs, _prop(app.view,"gallery_sort_val"), i)

            with dpg.menu(label="Filter:OFF") as mnuFilter:
                _bind(_BT.FormatLabel, _prop(app,"view"),
                      ["Filter:{}",
                       lambda view: "ON" if len(view.filter_str) \
                                         or view.filter_unassigned \
                                         or view.filter_radiosity \
                                         else "OFF"
                      ])

                ## [____________] filter
                dpg.add_input_text(label="filter")
                _bind(_BT.Value, _prop(app.view,"filter_str"))

                ## [ ] Textures without materials only
                dpg.add_checkbox(label="Textures without materials only")
                _bind(_BT.Value, _prop(app.view,"filter_unassigned"))

                ## [ ] Exclude radiosity textures
                dpg.add_checkbox(label="Exclude radiosity textures")
                _bind(_BT.Value, _prop(app.view,"filter_radiosity"))
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
        dpg.add_text("Other:")
        dpg.add_button(label="Open BSP in external viewer",
                       callback=lambda:app.do.open_external_viewer(
                                        app.data.bsppath,
                                        app.cfg["bsp_viewer"] )
                       )

        dpg.add_separator()
        with dpg.tree_node(label="NOTES",default_open=True):
            _bind(_BT.OptionsNote)
            dpg.add_text(consts.NOTES,wrap=0)


def add_about_dialog(app,tag,basepath=None):
    if basepath is None: basepath = get_base_path()
    ## Load images
    images = {
        #"app_icon": basepath.parent / "assets/images/BspTexRemap_64.png"
    }
    image_ids = {}
    with dpg.texture_registry() as texreg:
        for name, path in images.items():
            w,h,c,d = dpg.load_image(str(path))
            image_ids[name] = dpg.add_static_texture(width=w,height=h,default_value=d)

    # callback for buttons in howto's layout
    def howto_expando(sender,_,data):
        ''' callback fn to bind to dpg_lp, to be used on buttons laid out by it
            so that we can expand/collapse all nodes.
            data[0] is the target state (value)
            data[1:] is a list of root items whose children will be acted on
        '''
        target_state = bool(data[0])
        with dpg.mutex():
            for parent in data[1:]:
                for child in dpg.get_item_children(parent,1):
                    if dpg.get_item_type(child) == "mvAppItemType::mvTreeNode":
                        dpg.set_value(child, target_state)
    dpg_lp.add_named_callback("about:howto.expando", howto_expando)

    ## About dialog
    with dpg.window(label=f"{consts.GUI_APPNAME} Help", tag=tag,
                    show=False, width=600, height=450, no_scrollbar=True,
                    no_saved_settings=True,
                    on_close=app.view.update_window_state) as dlg_about:
        _bind_last_item(app,_BT.AboutDialog)

        with dpg.table(header_row=False,resizable=True):
            dpg.add_table_column(init_width_or_weight=80)
            dpg.add_table_column(init_width_or_weight=400)

            with dpg.table_row():
                with dpg.group():
                    #dpg.add_image(image_ids["app_icon"])
                    dpg.add_listbox([x["name"] for x in app.cfg["about_pages"]],
                                    default_value=app.cfg["about_pages"][0]["name"],
                                    width=-1,
                                    callback=lambda s,a,u:app.do.show_about(a))
                    _bind_last_item(app,_BT.AboutDialogListbox)

                    dpg.add_spacer()
                    dpg.add_button(label="Close", width=64,
                                   callback=lambda:dpg.hide_item(tag))

                with dpg.group() as content_group:
                    consts_dict = {x:getattr(consts,x) for x in dir(consts) if x.isupper()}
                    for i,pg_cfg in enumerate(app.cfg["about_pages"]):
                        layout_text = Path(basepath.parent / pg_cfg["layout_file"])\
                                      .read_text().format_map(consts_dict)
                        layout_thing = dpg_lp.parse_layout(layout_text)

                        page_tag = f"about:{pg_cfg['name']}"
                        with dpg.child_window(tag=page_tag,show=not i):
                            dpg_lp.layout_items(layout_thing, page_tag)


def add_misc_dialogs(app, binds={}):
    _bind = lambda *args,**kwargs: _bind_last_item(app,*args,**kwargs) # shorthand

    ## Edit summary
    with dpg.window(label="Edit summary", show=False,
                    no_saved_settings=True) as dlg_save_summary:
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


    ## Config Dialog
    with dpg.window(label="Settings", show=False, width=400,
                    no_saved_settings=True) as dlg_config:
        _bind(_BT.ConfigDialog)

        with dpg.collapsing_header(label="External programs",default_open=True):
            _browse = app.do.show_file_dialog

            # Bsp viewer - text input + browse button
            this_binding = _prop(app.cfg,"bsp_viewer")
            dpg.add_text("BSP viewer")
            with dpg.group(horizontal=True):
                dpg.add_input_text()
                _bind(_BT.Value, this_binding)
                dpg.add_button(label="Browse...",
                               callback=lambda:_browse(_BT.ExecutableFileDialog,
                                                bound_prop=this_binding))

            # External ecripts - text input + browse button
            ''' TODO
            this_binding = _prop(app.cfg,"post_exec")
            dpg.add_text("Execute this program/script after BSP save")
            with dpg.group(horizontal=True):
                dpg.add_input_text()
                _bind(_BT.Value, this_binding)
                dpg.add_button(label="Browse...",
                               callback=_filedlg_setprop_cb(app,this_binding))
            '''
        dpg.add_separator()
        dpg.add_button(label="Close", callback=lambda:dpg.hide_item(dlg_config))


def add_viewport_menu(app, dev_mode=False, basepath=None):
    ''' main window layout '''
    _bind = lambda *args,**kwargs: _bind_last_item(app,*args,**kwargs) # shorthand
    _mi = dpg.add_menu_item
    ___ = dpg.add_separator

    with dpg.viewport_menu_bar():

        with dpg.menu(label="BSP"):

            _mi(label="Open",
                shortcut=f'{mappings.key_binds_map["open_bsp_file"].text:>13s}',
                callback=_bare_cb(app.do.open_bsp_file))
            ___() # separator

            _mi(label="Save",
                shortcut=f'{mappings.key_binds_map["save_bsp_file"].text:>13s}',
                callback=lambda:app.do.save_bsp_file(app.data.backup))
            _mi(label="Save As",
                shortcut=f'{mappings.key_binds_map["save_bsp_file_as"].text:>13s}',
                callback=_bare_cb(app.do.save_bsp_file_as))
            ___()

            _mi(label="Reload",
                shortcut=f'{mappings.key_binds_map["reload"].text:>13s}',
                callback=app.do.reload)
            _mi(label="Close",
                shortcut=f'{mappings.key_binds_map["close"].text:>13s}',
                callback=lambda:app.do.close())
            ___()

            _mi(label="Exit",
                shortcut=f'{mappings.key_binds_map["quit"].text:>13s}',
                callback=lambda:app.do.quit())

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

        if basepath is None: basepath = get_base_path()
        init_path = basepath.with_suffix(".layout.ini")
        with dpg.menu(label="View"):
            _cb = app.view.update_window_state
            v_t = _mi(label="Textures",    check=True,callback=_cb,enabled=False)
            v_m = _mi(label="Materials",   check=True,callback=_cb)
            v_r = _mi(label="Remaps",      check=True,callback=_cb)
            v_o = _mi(label="Options",     check=True,callback=_cb)
            v_l = _mi(label="Log messages",check=True,callback=_cb)
            #v_a = _mi(label="About",       check=True,callback=_cb)
            ___()
            _mi(label="Save layout",
                callback=lambda:dpg.save_init_file(init_path))

            ___()
            _mi(label="Settings...", callback=app.do.show_config)

        app.view.window_binds[_BT.TexturesWindow]["menu"] = v_t
        app.view.window_binds[_BT.MaterialsWindow]["menu"] = v_m
        app.view.window_binds[_BT.RemapsWindow]["menu"] = v_r
        app.view.window_binds[_BT.OptionsWindow]["menu"] = v_o
        app.view.window_binds[_BT.LogWindow]["menu"] = v_l
        #app.view.window_binds[_BT.AboutDialog]["menu"] = v_a

        if dev_mode:
            with dpg.menu(label="Debug"):
                _mi(label="GUI item registry",
                    callback=lambda *_:dpg.show_item_registry())
                _mi(label="GUI style editor",
                    callback=lambda *_:dpg.show_style_editor())
                _mi(label="Show loading",check=True,
                    callback=lambda s,a,u:gui_utils.show_loading(a))

        with dpg.menu(label="Help"):
            #_mi(label=pg_cfg["About",callback=lambda:app.do.show_about(0))
            for pg_cfg in app.cfg["about_pages"]:
                if "help_menu_item" not in pg_cfg \
                or not pg_cfg["help_menu_item"]: continue

                cb = lambda page: lambda:app.do.show_about(page)
                _mi(label=pg_cfg["name"], callback=cb(pg_cfg["name"]))


def main(basepath, start=True):
    ''' basepath is the path to the main script (unbundled) or bundled exe
        set start to False for test and debug
    '''
    args = parse_arguments(gui=True)
    setup_logger(args.log) # for console log
    log = logging.getLogger() ## "__main__" should use the root logger

    dpg.create_context()
    # must be called before create_viewport
    dpg.configure_app(docking=True, docking_space=True,
                      init_file=basepath.with_suffix(".layout.ini"))

    # generate IDs - the IDs are used by the init file, they must be the
    #                same between sessions
    materials_window = dpg.generate_uuid()
    remaps_window    = dpg.generate_uuid()
    textures_window  = dpg.generate_uuid()
    options_window   = dpg.generate_uuid()
    log_window       = dpg.generate_uuid()
    about_dialog     = dpg.generate_uuid()

    window_binds = {
        _BT.TexturesWindow : {"window": textures_window},
        _BT.MaterialsWindow: {"window": materials_window},
        _BT.RemapsWindow   : {"window": remaps_window},
        _BT.OptionsWindow  : {"window": options_window},
        _BT.LogWindow      : {"window": log_window},

        #_BT.AboutDialog    : {"window": about_dialog},
    }


    app = App(basepath)
    app.view.window_binds = window_binds
    dpg_dnd.initialize()
    dpg_dnd.set_drop(app.do.handle_drop)
    dpg_lp.setup(asset_base_path = get_base_path().parent)

    colors.setup_themes(app.cfg)
    colors.setup_fonts(basepath.parent/"assets/fonts")
    dpg.bind_font(colors.AppFonts.Regular.tag)


    # setup log window
    gui_utils.DpgLogHandler.TAG = log_window
    log.addHandler(gui_utils.DpgLogHandler(0,on_close=app.view.update_window_state))
    dpg.bind_item_theme(gui_utils.DpgLogHandler.TAG,colors.AppThemes.LogMessage)

    # setup the other windows
    add_file_dialogs(app)
    add_viewport_menu(app,args.dev,basepath)
    add_materials_window(app,materials_window)
    add_wannabe_window(app,remaps_window)
    add_textures_window(app,textures_window)
    add_options_window(app,options_window)
    add_about_dialog(app,about_dialog,basepath)
    add_misc_dialogs(app,{
        _BT.AboutDialog: about_dialog,
    })

    #app.view.reflect()
    app.view.update_window_state(0,0)

    if args.bsppath:
        app.data.load_bsp(args.bsppath)
    app.view.set_viewport_ready() # this will reschedule itself to run later

    dpg.create_viewport(title=consts.GUI_APPNAME)#, width=1200, height=800)
    dpg.set_viewport_large_icon(basepath.parent / "assets/images/BspTexRemap_64.ico")
    dpg.set_viewport_small_icon(basepath.parent / "assets/images/BspTexRemap_64.ico")
    dpg.setup_dearpygui()
    dpg.show_viewport()

    if start:
        dpg.start_dearpygui() # dpg main loop

        app.save_config()
        dpg.destroy_context()
    
    else:
        return app


if __name__ == "__main__":
    basepath = get_base_path()
    main(basepath)

