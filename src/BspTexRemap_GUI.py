import dearpygui.dearpygui as dpg
import DearPyGui_DragAndDrop as dpg_dnd
import logging
from pathlib import Path
from collections import namedtuple
from jankbsp import BspFileBasic as BspFile
from jankbsp.types import EntityList
from bsptexremap.common import parse_arguments, setup_logger
from bsptexremap.enums import MaterialEnum as ME
from bsptexremap.materials import MaterialSet # matchars
from bsptexremap.dpg.modelcontroller import App
from bsptexremap.dpg.galleryview import GalleryView
from bsptexremap.dpg.textureview import TextureView
from bsptexremap.dpg import mappings, gui_utils, colors
BindingType = mappings.BindingType # puts it onto the main scope
_propbind = namedtuple("PropertyBinding",["obj","prop"])

def _help(message):
    return gui_utils.add_help_in_place(message)
def _sort_table(sender, sort_specs):
    return gui_utils.sort_table(sender, sort_specs)
def _bind_last_item(app,*args,**kwargs):
    return app.view.bind(dpg.last_item(),*args,**kwargs)

def main():
    dpg.create_context(); dpg_dnd.initialize()

    args = parse_arguments(gui=True)
    setup_logger(args.log)
    log = logging.getLogger(__name__)
    logging.getLogger().addHandler(gui_utils.DpgHandler(show=False))

    app = App()
    dpg_dnd.set_drop(app.do.handle_drop)
    colors.add_themes()
    def _bind(*args,**kwargs): _bind_last_item(app,*args,**kwargs) # shorthand

    file_dlg_cfg = {
        BindingType.BspOpenFileDialog : {
            "tag" : "dlgBspFileOpen",
            "label": "Open BSP file",
            "callback": app.do.open_file,
            "exts": ("bsp","all")
        },
        BindingType.BspSaveFileDialog : {
            "tag" : "dlgBspFileSaveAs",
            "label": "Save BSP file",
            "callback": app.do.save_file_as,
            "exts": ("bsp","all")
        },
        BindingType.MatLoadFileDialog : {
            "tag" : "dlgMatFileOpen",
            "label": "Open materials file",
            "callback": app.do.load_mat_file,
            "exts": ("txt","all")
        },
        BindingType.MatExportFileDialog : {
            "tag" : "dlgMatFileExport",
            "label": "Export custom materials file",
            "callback": app.do.export_custommat,
            "exts": ("txt","all")
        }
    }
    for type, item in file_dlg_cfg.items():
        app.view.bind(gui_utils.create_file_dialog(**item), type)


    with dpg.window(tag="Primary Window",no_scrollbar=True):
        dpg.bind_item_theme(dpg.last_item(),"theme:main_window")
        with dpg.menu_bar():
            with dpg.menu(label="BSP"):
                dpg.add_menu_item(label="Open", callback=app.do.show_open_file)
                dpg.add_separator()
                dpg.add_menu_item(label="Save", callback=app.do.save_file)
                dpg.add_menu_item(label="Save As", callback=app.do.show_save_file_as)
                dpg.add_separator()
                dpg.add_menu_item(label="Reload", callback=app.do.reload)
                dpg.add_separator()
                dpg.add_menu_item(label="Exit", callback=exit)

            with dpg.menu(label="Materials"):
                dpg.add_menu_item(label="Load",
                                  callback=app.do.show_open_mat_file)
                dpg.add_menu_item(label="Export custom materials",
                                  callback=app.do.export_custommat)
                dpg.add_separator()
                dpg.add_menu_item(label="Auto-load from BSP path",check=True)
                _bind(BindingType.Value, _propbind(app.data,"auto_load_materials"))

        with dpg.table(resizable=True,height=-8) as mainLayoutTable: # header_row=False,
            dpg.bind_item_theme(dpg.last_item(),"theme:layout_table")
            col1 = dpg.add_table_column(label="Materials",width=200)
            col2 = dpg.add_table_column(label="Textures",init_width_or_weight=3)
            dpg.add_table_column(label="Options/Actions",width=200)

            app.view.bind(col1, BindingType.FormatLabel,
                          _propbind(app.data,"mat_set"),
                          data=["Materials {}",
                                lambda mat: f"({len(+mat)}/{len(mat)})" \
                                if app.data.matpath else ""])

            app.view.bind(col2, BindingType.FormatLabel,
                          _propbind(app,"view"),
                          data=["Textures {}",
                                lambda view: "({}M + {}X = {}T, {}V)"\
                                .format(len(view.app.data.bsp.textures_m),
                                        len(view.app.data.bsp.textures_x),
                                        len(view.app.data.bsp.textures),
                                        len(view.gallery.data)
                                ) if view.app.data.bsp else ""])

            with dpg.table_row() as mainLayoutRow:

                # materials pane
                with dpg.child_window(border=False):
                    dpg.bind_item_theme(dpg.last_item(),"theme:normal_table")
                    app.view.bind( dpg.add_input_text(label="path",readonly=True),
                                   BindingType.Value,
                                   _propbind(app.data,"matpath") )
                    dpg.add_button(label="Load...",callback=app.do.show_open_mat_file)

                    with dpg.collapsing_header(label="Summary",default_open=True):
                        app.view.bind( dpg.add_table(resizable=True),
                                       BindingType.MaterialSummaryTable )

                    with dpg.collapsing_header(label="Entries"):
                        app.view.bind( dpg.add_input_text(label="filter type",
                                        hint=f"Material chars e.g. {MaterialSet.MATCHARS}"),
                                       BindingType.Value,
                                       _propbind(app.view,"filter_matchars") )
                        app.view.bind( dpg.add_input_text(label="filter name",
                                                          hint=f"Material name"),
                                       BindingType.Value,
                                       _propbind(app.view,"filter_matnames") )
                        app.view.bind( dpg.add_table(resizable=True, sortable=True,
                                                     callback=_sort_table),
                                       BindingType.MaterialEntriesTable )

                    with dpg.collapsing_header(label="Remaps",default_open=True):
                        with dpg.table(header_row=False):
                            for i in range(2): dpg.add_table_column()
                            with dpg.table_row():
                                dpg.add_checkbox(label="grouped")
                                _bind(BindingType.Value,_propbind(app.view,"texremap_grouped"))
                                dpg.add_checkbox(label="hide empty")
                                _bind(BindingType.Value,_propbind(app.view,"texremap_not_empty"))
                            with dpg.table_row():
                                dpg.add_checkbox(label="sort")
                                _bind(BindingType.Value,_propbind(app.view,"texremap_sort"))
                                dpg.add_checkbox(label="reverse")
                                _bind(BindingType.Value,_propbind(app.view,"texremap_revsort"))
                        dpg.add_separator()
                        dpg.add_group()
                        _bind(BindingType.TextureRemapList)

                    app.view.render_material_tables()

                # textures pane
                with dpg.child_window(autosize_y=False,menubar=True,
                                      horizontal_scrollbar=True) as winTextures:
                    dpg.bind_item_theme(dpg.last_item(),"theme:normal_table")
                    with dpg.menu_bar():
                        with dpg.menu(
                                label="Show:All",
                                user_data=["gallery_show_text"]
                        ) as mnuTexShow:
                            app.view.bind(mnuTexShow, BindingType.FormatLabel,
                                          _propbind(app.view,"gallery_show_val"),
                                          data=["Show:{:.3s}", mappings.gallery_show])
                                          #  -> mappings.gallery_show[app.view.gallery_show_val]

                            app.view.bind(dpg.add_radio_button(mappings.gallery_show,
                                                               horizontal=True),
                                          BindingType.TextMappedValue,
                                          _propbind(app.view,"gallery_show_val"),
                                          data=mappings.gallery_show )
                            dpg.add_separator()

                            app.view.bind( dpg.add_text("Referenced WAD files"),
                                           BindingType.FormatValue,
                                           _propbind(app.view, "wadstats"),
                                           ["Referenced WAD files: {}",
                                            lambda stats:len(stats) ] )
                            app.view.bind( dpg.add_group(tag="grpWadlist"),
                                           BindingType.WadListGroup )

                            def _select_all_wads(value=True):
                                for child in dpg.get_item_children("grpWadlist", 1):
                                    dpg.set_value(child,value)

                            with dpg.group(horizontal=True):
                                dpg.add_checkbox(label="All",
                                                 callback=lambda s,a,u:_select_all_wads(a))
                                dpg.add_button(label="load selected",
                                               callback=app.do.load_selected_wads)

                        with dpg.menu(label="Size:Stuff") as mnuTexSize:
                            app.view.bind(
                                    mnuTexSize,
                                    BindingType.FormatLabel,
                                    _propbind(app.view,"gallery_size_val"),
                                    data = [
                                        "Size:{}",
                                        lambda _:"{:.2f}x/{}px".format(
                                                app.view.gallery_size_scale,
                                                app.view.gallery_size_maxlen
                                        )
                                    ]
                            )
                            for i, text in enumerate(mappings.gallery_sizes):
                                app.view.bind( dpg.add_menu_item(label=text,check=True),
                                               BindingType.ValueIs,
                                               _propbind(app.view,"gallery_size_val"),
                                               i )
                            app.view.bind(
                                    dpg.add_slider_float(
                                            label="scale",
                                            max_value=16.0,
                                            clamped=True
                                    ),
                                    BindingType.Value,
                                    _propbind(app.view,"gallery_size_scale")
                            )
                            app.view.bind(
                                    dpg.add_slider_int(
                                            label="max len.",
                                            max_value=2048,
                                            default_value=512,
                                            clamped=True
                                    ),
                                    BindingType.Value,
                                    _propbind(app.view,"gallery_size_maxlen")
                            )
                        with dpg.menu(label="Filter:OFF") as mnuFilter:
                            app.view.bind(
                                    mnuFilter,
                                    BindingType.FormatLabel,
                                    _propbind(app,"view"),
                                    data = [
                                        "Filter:{}",
                                        lambda view: "ON" if len(view.filter_str) \
                                                          or view.filter_unassigned \
                                                          or view.filter_radiosity \
                                                          else "OFF"
                                    ]
                            )
                            app.view.bind(
                                    dpg.add_input_text(label="filter"),
                                    BindingType.Value,
                                    _propbind(app.view,"filter_str")
                            )
                            app.view.bind(
                                    dpg.add_checkbox(label="Textures without materials only"),
                                    BindingType.Value,
                                    _propbind(app.view,"filter_unassigned")
                            )
                            app.view.bind(
                                    dpg.add_checkbox(label="Exclude radiosity textures"),
                                    BindingType.Value,
                                    _propbind(app.view,"filter_radiosity")
                            )
                            _help("These are textures embedded by VHLT+'s RAD to make translucent objects light properly")
                        with dpg.menu(label="Selection"):
                            dpg.add_menu_item(label="Select all",
                                              user_data=True,
                                              callback=app.do.select_textures)
                            dpg.add_menu_item(label="Select none",
                                              user_data=False,
                                              callback=app.do.select_textures)
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

                    with dpg.group() as gallery_root:
                        app.view.bind( gallery_root, BindingType.GalleryRoot )

                def _center_resize():
                    app.view.gallery.render() # reflow the gallery view
                with dpg.item_handler_registry() as resize_handler:
                    dpg.add_item_resize_handler(callback=_center_resize)

                app.view.gallery.submit(gallery_root,winTextures)
                #dpg.bind_item_handler_registry(mainLayoutTable, resize_handler)
                #dpg.bind_item_handler_registry(winTextures, resize_handler)
                dpg.bind_item_handler_registry("Primary Window", resize_handler)

                # options/actions pane
                with dpg.child_window(border=False):
                    dpg.bind_item_theme(dpg.last_item(),"theme:normal_table")

                    dpg.add_text("On load:")
                    app.view.bind( dpg.add_checkbox(label="Auto find and load materials"),
                                   BindingType.Value,
                                   _propbind(app.data,"auto_load_materials") )
                    app.view.bind( dpg.add_checkbox(label="Auto find and load WADs"),
                                   BindingType.Value,
                                   _propbind(app.data,"auto_load_wads") )

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
                    app.view.bind( dpg.add_radio_button(mappings.remap_entity_actions,indent=16),
                                   BindingType.TextMappedValue,
                                   _propbind(app.data,"remap_entity_action"),
                                   data=mappings.remap_entity_actions )

                    dpg.add_text("")

                    dpg.add_button(label="Save BSP", callback=app.do.save_file)
                    _help("Remaps texture and save in the same file")

                    app.view.bind( dpg.add_checkbox(label="Backup", indent=8),
                                   BindingType.Value,
                                   _propbind(app.data,"backup") )
                    _help("Makes backup before saving")

                    dpg.add_button(label="Save BSP as...",
                                   callback=app.do.show_save_file_as)
                    _help("Remaps texture and save in another file")

                    dpg.add_button(
                            label="Export custom materials",
                            callback=app.do.show_save_mat_file
                    )
                    _help("Generates custom material file that can be used\nwith BspTexRemap.exe (the console program)")

    app.view.reflect()
    if args.bsppath:
        app.data.load_bsp(args.bsppath)
    dpg.set_frame_callback(1,callback=lambda:app.view.set_viewport_ready())

    #dpg.show_item_registry()

    dpg.create_viewport(title='BspTexRemap GUI', width=1200, height=800)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("Primary Window", True)

    dpg.start_dearpygui()
    dpg.destroy_context()

if __name__ == "__main__":
    main()
