''' MVC for the GUI app
'''
import dearpygui.dearpygui as dpg

from . import mappings, gui_utils
from .mappings import BindingType, RemapEntityActions
from .textureview import TextureView
from .galleryview import GalleryView
from .dbgtools import *
from .colors import MaterialColors

from .. import consts, utils
from ..enums import MaterialEnum, DumpTexInfoParts
from ..common import search_materials_file, search_wads, filter_materials, get_textures_from_wad, dump_texinfo
from ..utils import failure_returns_none
from ..bsputil import wadlist, guess_lumpenum, bsp_custommat_path
from ..materials import MaterialSet, TextureRemapper

from jankbsp import BspFileBasic as BspFile, WadFile
from jankbsp.types import EntityList
from jankbsp.types.wad import WadMipTex

from pathlib import Path
from dataclasses import dataclass, field #, asdict
from collections import namedtuple
from typing import NamedTuple, ClassVar
from operator import attrgetter
from itertools import chain
from concurrent.futures import ThreadPoolExecutor
import re, logging

log = logging.getLogger(__name__)


@dataclass
class WadStatus:
    #app: any # reference to app
    name : str
    found : bool = None # true=yes,false=no,none=no action
    loaded : bool = None # true=yes,no=can't load,none=no action
    selected : bool = False
    uuid : any = None
    path : Path = None
    loaded_count : int = 0
    _found_str = {True:"found",False:"not found",None:""}
    _loaded_str = {True:"loaded",False:"can't load",None:""}
    _parent: ClassVar = None

    def _fmt(self):
        # 1: found/not found, 2: loaded, 3: loaded_count
        if self.loaded:              fmt_str = "{0} ({1}, {3} {2})"
        elif self.loaded == False:   fmt_str = "{0} ({1}, {2})"
        elif self.found is not None: fmt_str = "{0} ({1})"
        else: return self.name
        return fmt_str.format(self.name, self._found_str[self.found],
                                         self._loaded_str[self.loaded],
                              self.loaded_count)

    def __post_init__(self):
        callback = lambda s,a,u: setattr(self,"selected",a)
        self.uuid = dpg.add_selectable(label=self._fmt(),
                                       parent=self._parent,
                                       disable_popup_close=True,
                                       callback=callback)

    def delete(self):
        if self.uuid: dpg.delete_item(self.uuid)

    def update(self, found=None, loaded=None, loaded_count=None):
        if found is not None: self.found = found
        if loaded: self.loaded = loaded
        if loaded_count: self.loaded_count = loaded_count
        dpg.configure_item(self.uuid,
                           label=self._fmt(),
                           enabled=False if self.found is False else True)


@dataclass
class AppModel:
    app : any # reference to app
    # primary data
    bsppath : Path    = None
    bsp     : BspFile = None
    matpath : Path    = None
    mat_set     : MaterialSet = field(default_factory=MaterialSet)
    wannabe_set : MaterialSet = field(default_factory=MaterialSet)

    matchars : str    = MaterialSet.MATCHARS # edit if loading CZ/CZDS

    # settings
    auto_load_materials : bool = True # try find materials.path
    auto_load_wads      : bool = True # try find wads
    auto_parse_ents     : bool = True # parse entity
    remap_entity_action : int  = 0    # RemapEntityActions.Insert
    backup              : bool = True # creates backup file if saving in same file

    def load_bsp(self, bsppath):
        ''' loads given bsp, and kickstarts some post-load operations
            (has side effects)
        '''
        ## load bsp
        log.info(f"Loading BSP: {bsppath!s}")
        self.bsppath = Path(bsppath)
        with open(self.bsppath, "rb") as f:
            self.bsp = BspFile(f, lump_enum=guess_lumpenum(self.bsppath))

        ## load textures
        self.app.view.load_textures(self.bsp.textures)

        ## setup material set
        if self.auto_load_materials:
            matpath = search_materials_file(self.bsppath)
            if matpath:
                self.load_materials(matpath) # sets self.matpath and render the tables
        else:
            self.matpath = None
        self.app.view.render_material_tables() # manually render tables

        ## setup wannabe set
        self.wannabe_set = MaterialSet()
        self.app.view.update_wannabe_material_tables()

        ## setup wad
        self.app.view.update_wadlist() # populates app.view.wad_found_paths
        if self.auto_load_wads:
            paths_to_load = tuple(v for k,v in self.app.view.wad_found_paths.items() if v)
            self.app.view.load_external_wad_textures(paths_to_load)

        log.info("Done.")

    def load_materials(self, matpath):
        self.matpath = Path(matpath)
        self.mat_set = MaterialSet.from_materials_file(self.matpath)
        self.app.view.reflect()
        self.app.view.render_material_tables()


@dataclass(frozen=True)
class BindingEntry:
    type : BindingType
    prop : namedtuple = None
    data : any = None
    update_predicate  : callable = None
    reflect_predicate : callable = None


@dataclass
class AppView:
    # the parent app
    app : any
    # dict of bound items
    bound_items : dict           = field(default_factory=dict)

    # list of wadstatus
    wadstats: list[WadStatus]    = field(default_factory=list)
    wad_found_paths : dict       = field(default_factory=dict)
    # all textures in the bsp
    textures : list[TextureView] = field(default_factory=list)
    # gallery view (only store the filtered items in its data)
    gallery : GalleryView        = field(default_factory=GalleryView)

    # check against issuing dpg commands when viewport isn't ready
    _viewport_ready : bool       = False

    # material entry filter settings
    filter_matchars : str        = ""
    filter_matnames : str        = ""

    # texture remap list settings
    texremap_sort : bool         = False
    texremap_revsort : bool      = False
    texremap_grouped : bool      = False
    texremap_not_empty : bool    = False

    # texture gallery view settings
    gallery_show_val : int       = 2 # all  -> mappings.gallery_show_map
    gallery_size_val : int       = 1 # full -> mappings.gallery_size_map
    gallery_size_scale : float   = 1
    gallery_size_maxlen:int|float= 512
    gallery_sort_val : int       = 0 # no sort
    filter_str : str             = ""
    filter_unassigned : bool     = False # show only textures without materials
    filter_radiosity : bool      = False # hide radiosity generated textures
    selection_mode : bool        = False
    _gallery_view_props = [ # use to watch updated values and fire gallery render
        "gallery_show_val",
        "gallery_size_val",
        "gallery_size_scale",
        "gallery_size_maxlen",
        "gallery_sort_val",
        "filter_str",
        "filter_unassigned",
        "filter_radiosity"
    ]


    def bind(self, tag, type:BindingType, prop=None, data=None,
             update_predicate=None, reflect_predicate=None):
        ''' binds the tag to the prop
            prop is a tuple of obj and propname.
            - get value using getattr(*prop)
            - set value using setattr(*prop, value)
            data is usually passed by value
            update_predicate is a callable that checks whether it should update
            reflect_predicate is a callable that checks whether it should run on reflect
        '''
        self.bound_items[tag] = BindingEntry(type, prop, data)
        if type in mappings.writeable_binding_types:
            dpg.configure_item(tag, callback=self.update)


    def update(self,sender,app_data,*_):
        ''' called by the gui item when it updates a prop linked to the model
            prop is a tuple of obj and propname.
            - set value using setattr(*prop, value)
        '''
        if sender not in self.bound_items: return
        item = self.bound_items[sender]
        if callable(item.update_predicate) and not item.update_predicate(): return

        if item.type == BindingType.Value:
            setattr(*item.prop, app_data)
        elif item.type == BindingType.ValueIs:
            setattr(*item.prop, item.data)
        elif item.type == BindingType.TextMappedValue:
            val = self._index_of(item.data,lambda x:x == app_data)
            if val is not None: setattr(*item.prop, val)

        ### update specific things based on prop ###
        ## material entries filter changed
        if item.prop[0] == self and item.prop[1].startswith("filter_mat"):
            self.render_material_tables(False,True) # update only entries

        ## gallery size option change
        elif item.prop[0] == self and item.prop[1] in \
        ["gallery_size_scale", "gallery_size_maxlen"]:
            self.gallery_size_val = len(mappings.gallery_size_map) - 1

        ## gallery size slider change
        elif tuple(item.prop) == (self,"gallery_size_val") \
        and self.gallery_size_val < len(mappings.gallery_size_map) - 1:
            _, self.gallery_size_scale, self.gallery_size_maxlen \
                    = mappings.gallery_size_map[self.gallery_size_val]

        ## any of the gallery settings changed
        if item.prop[0] == self and item.prop[1] in self._gallery_view_props:
            self.reflect() # general total reflection
            self.update_gallery(size_only = (item.prop[1]=="gallery_size_val"))

        ## texture remap view settings
        elif item.prop[0] == self and item.prop[1][0:9] == "texremap_":
            self.update_wannabe_material_tables()

        ## updates other bound items with same prop
        else:
            self.reflect(not_tagged=sender,
                         prop=item.prop,
                         types=mappings.reflect_all_binding_types)


    def reflect(self, not_tagged=None, prop=None, types=mappings.reflect_all_binding_types):
        ''' updates all bound items (optionally of given prop)
            prop is a tuple of obj and propname.
            - get value using getattr(*prop)
        '''
        if self._viewport_ready:
            if self.app.data.bsppath:
                dpg.set_viewport_title(f"{self.app.data.bsppath} - BspTexRemap GUI")
            else:
                dpg.set_viewport_title("BspTexRemap GUI")

        for tag,item in self.bound_items.items():
            if tag == not_tagged: continue
            elif prop:
                if (item.prop and tuple(item.prop) != tuple(prop)) \
                or item.prop != prop: continue
            elif item.type not in types \
            or callable(item.reflect_predicate) and not item.reflect_predicate():
                continue

            if item.type == BindingType.Value:
                dpg.set_value(tag, getattr(*item.prop))
            elif item.type == BindingType.ValueIs:
                dpg.set_value(tag, getattr(*item.prop) == item.data)
            elif item.type == BindingType.TextMappedValue:
                val = item.data(getattr(*item.prop)) if callable(item.data) \
                        else item.data[getattr(*item.prop)]
                dpg.set_value(tag, val)
            # these are readonly
            elif item.type in [BindingType.FormatLabel, BindingType.FormatValue]:
                label, *attrs = item.data
                attr_values = tuple( x(getattr(*item.prop)) if callable(x) \
                                else x[getattr(*item.prop)] for x in attrs )
                if item.type == BindingType.FormatValue:
                    dpg.set_value(tag,label.format(*attr_values))
                else:
                    dpg.configure_item(tag, label=label.format(*attr_values))

    def get_bound_entries(self,prop=None,type:BindingType=None):
        for k,v in self.bound_items.items():
            if (prop and v.prop == prop) or v.type == type:
                yield (k, self.bound_items[k])

    def get_bound_entry(self,prop=None,type:BindingType=None):
        return next(self.get_bound_entries(prop,type),None)

    def get_dpg_item(self,type:BindingType=None):
        ''' use this to get only the dpg tag '''
        return self.get_bound_entry(type=type)[0]

    def _index_of(self, collection, callable):
        for i, thing in enumerate(collection):
            if callable(thing):
                return i

    def set_viewport_ready(self):
        self._viewport_ready = True
        self.reflect()
        self.update_gallery()


    def load_textures(self, miptexes, update=False, new_source=None):
        ''' populates app.view.textures with TextureView items.
            if updating, the miptexes are from wads, and new_source must be
            the wad's filename.

            on both cases, returns the number of textures loaded/updated
        '''
        result = 0

        if update:
            ''' build a list of new miptexes, pair it up with the corresponding
                texview item, then use the thread pool to update them
            '''
            finder = lambda tex:tex.name.lower() == newtex.name.lower()
            update_args = [] # tuple of texview,newmiptex,source_location
            for newtex in miptexes:
                if (oldtex := next(filter(finder,self.textures),None)):
                    update_args.append((oldtex,newtex,new_source))

            if not len(update_args): return
            log.info(f"{len(update_args)} texture entries will be updated with {new_source}")
            # transpose list i.e. list 1 is all the texview, #2 is all the miptex, etc.
            argsT = [[row[i] for row in update_args] for i in range(len(update_args[0]))]
            log.debug(f"START UPDATE TEXTURES ({len(argsT[0])})")
            with time_it():
                with ThreadPoolExecutor() as executor:
                    for result in executor.map(TextureView.static_update,*argsT):
                        pass
            result = len(argsT[0])

        else:
            log.info(f"Loading textures ({len(miptexes)} items)")
            # self.textures = [TextureView.from_miptex(item) for item in miptexes]
            # TEST parallel texture conversion
            loaded_textures = []
            with time_it():
                with ThreadPoolExecutor() as executor:
                    for result in executor.map(TextureView.from_miptex,miptexes):
                        loaded_textures.append(result)

            self.textures = loaded_textures
            result = len(loaded_textures)

        if self._viewport_ready: self.update_gallery()
        return result


    def load_external_wad_textures(self,wadpaths:tuple[Path]):
        ''' loads the textures from the wads, *in order*, then update textures list.
            caller should filter the wad paths, and make sure it's in the same
            order as in the bsp, to preserve game engine presumed load order.
        '''
        wanted_list = [x.name for x in self.app.data.bsp.textures_x]
        log.info(f"{len(wanted_list)} external textures wanted")
        if not len(wanted_list): return

        log.info(f"loading all wad files simultaneously-ish...")
        taskfn = get_textures_from_wad# failure_returns_none(get_textures_from_wad)
        results = {}
        log.debug("START")
        with time_it():
            with ThreadPoolExecutor() as executor:
                for wadpath, result \
                in zip(wadpaths, executor.map(taskfn, wadpaths,
                                              [wanted_list]*len(wadpaths))):
                    results[wadpath] = result

        for wadpath in wadpaths:
            wadname = Path(wadpath).name
            status = {"loaded": False if results[wadpath] is None else True}
            if results[wadpath] is None:
                log.warning(f"failed to load textures from {wadname}")

            elif len(results[wadpath]):
                # something is loaded (empty means can load but found nothing)
                log.debug(f"updating textures with {wadname} ({len(results[wadpath])} items)")

                # fix the miptex name to the waddirentry's.
                # I'm not sure if the engine only considers the waddirentry's name
                # but it makes sense
                # NOTE: result is a dict. translate to list
                miptexes = []
                for direntryname, miptex in results[wadpath].items():
                    miptex.name = direntryname
                    miptexes.append(miptex)

                status["loaded_count"] = self.load_textures(miptexes, True, wadname)
            else:
                status["loaded_count"] = 0

            log.debug(f"updating wadstats for {wadname}")
            item = next(filter(lambda x:x.name==wadname,self.wadstats),None)
            if item: item.update(**status)


    def update_wadlist(self):
        WadStatus._parent = self.get_dpg_item(type=BindingType.WadListGroup)
        wads = wadlist(self.app.data.bsp.entities,True)

        list(x.delete() for x in self.wadstats) # make sure the bound dpg item is deleted
        self.wadstats = [WadStatus(w) for w in wads]

        wad_found_paths = search_wads(self.app.data.bsppath, wads)
        for item in self.wadstats:
            item.update(found=bool(wad_found_paths[item.name]))
            item.path = wad_found_paths[item.name]
        self.wad_found_paths = wad_found_paths

        self.reflect() #prop=_propbind(self, "wadstats"))


    def update_gallery(self, size_only=False):
        ''' filters the textures list, then passes it off to gallery to render '''
        # all the filters in modelcontroller assembled
        f_a = mappings.gallery_show_map[self.gallery_show_val].filter_fn
        f_u = lambda item: item.matname not in self.app.data.mat_set
        f_r = lambda item: not item.name.lower().startswith("__rad")
        f_s = lambda item: utils.filterstring_to_filter(self.filter_str)(item.name)
        # the sort
        s_k = mappings.gallery_sort_map[self.gallery_sort_val].key
        s_r = mappings.gallery_sort_map[self.gallery_sort_val].reverse

        if not size_only:
            # assemble the filter stack
            the_list = filter(f_a,self.textures)
            if self.filter_unassigned:
                the_list = filter(f_u, the_list)
            if self.filter_radiosity:
                the_list = filter(f_r, the_list)
            if self.filter_str:
                the_list = filter(f_s, the_list)
            # filter, sort, map, send to print (to gallery)
            self.gallery.data = list(sorted(the_list, key=s_k, reverse=s_r))
            for item in self.gallery.data: item.selected=False

        # set gallery scale
        if self.gallery_size_val == len(mappings.gallery_size_map) - 1:
            # last item == custom
            self.gallery.scale = self.gallery_size_scale
            self.gallery.max_length = self.gallery_size_maxlen
        else:
            size_tuple = mappings.gallery_size_map[self.gallery_size_val]
            self.gallery.scale = size_tuple.scale
            self.gallery.max_length = size_tuple.max_length

        # render the gallery
        self.gallery.render()
        self.reflect(prop=(self.app,"view"))


    def render_material_tables(self, summary=True, entries=True):
        ME = MaterialEnum
        mat_set = self.app.data.mat_set
        choice_set = mat_set.choice_cut()
        wannabe_set = self.app.data.wannabe_set

        mat_color = lambda mat: MaterialColors[mat].color
        avail_colors = lambda n: (0,255,0) if n else (255,0,0)
        is_suitable = lambda name: \
                consts.MATNAME_MIN_LEN <= len(name) <= consts.MATNAME_MAX_LEN
        suitable_mark = lambda name: "Y" if is_suitable(name) else "N"
        suitable_colors = lambda name: (0,255,0) if is_suitable(name) else (255,0,0)

        ### SUMMARY TABLE
        if summary:
            header = (("",0.4), ("Material",1.8), "Count", "Usable", "Assigned")
            data = []
            for mat in mat_set.MATCHARS:
                data.append([ ( ME(mat).value, {"color": mat_color(mat)} ),
                                ME(mat).name,
                                len(mat_set[mat]),
                              ( len(choice_set[mat]),
                                {"color" : avail_colors(len(choice_set[mat]))} ),
                              len(wannabe_set[mat]) ])
            # totals row
            data.append(["", "TOTAL", len(mat_set), len(choice_set), len(wannabe_set)])

            table = self.get_dpg_item(type=BindingType.MaterialSummaryTable)
            gui_utils.populate_table(table, header, data)

        ### ENTRIES TABLE
        if entries:
            filtered_set = filter_materials(mat_set,
                                            self.filter_matchars,
                                            self.filter_matnames)
            header = (("Mat",0.4), ("Name",3), "Usable")
            data = []
            for mat in self.app.data.matchars:
                for name in filtered_set[mat]:
                    data.append([(ME(mat).value, {"color": mat_color(mat)}),
                                  name,
                                 (suitable_mark(name), {"color":suitable_colors(name)})])
            table = self.get_dpg_item(type=BindingType.MaterialEntriesTable)
            gui_utils.populate_table(table, header, data)


    def update_wannabe_material_tables(self):
        ''' update the summary table display of wannabe set items '''
        table = self.get_dpg_item(type=BindingType.MaterialSummaryTable)

        for i, mat in enumerate(self.app.data.wannabe_set.MATCHARS):
            table_cell = gui_utils.traverse_children(table, f"{i}.4")
            dpg.set_value(table_cell, len(self.app.data.wannabe_set[mat]))

        totals_row = len(self.app.data.wannabe_set.MATCHARS)
        table_cell = gui_utils.traverse_children(table, f"{totals_row}.4")
        dpg.set_value(table_cell, len(self.app.data.wannabe_set))

        ### START RENDERING THE TEXTURE REMAP LIST ###
        ME = MaterialEnum
        _E = gui_utils.ImglistEntry
        dict_of_lists = {}
        target_len = 48

        for mat in self.app.data.wannabe_set.MATCHARS:
            sublist = []

            for matname in self.app.data.wannabe_set[mat]:

                textures = [x for x in self.textures if x.matname==matname]
                text = f"{matname}" if self.texremap_grouped else \
                       f"{matname} {'-'*(15-len(matname))}> {mat}"

                if len(textures):
                    sample = textures[0]
                    entry = _E(sample.uuid,sample.width,sample.height,
                               [text, f"{len(textures)} items"], matname)
                else:
                    entry = _E(None,target_len,target_len,
                               [text, "0 items"], matname)

                sublist.append(entry)

            dict_of_lists[ME(mat).name] = sublist

        if not self.texremap_grouped:
            dict_of_lists = {"All":list(chain(*dict_of_lists.values()))}

        if self.texremap_sort:
            for sublist in dict_of_lists.values():
                sublist.sort(key=lambda x:x.key, reverse=self.texremap_revsort)

        remap_list = self.get_dpg_item(type=BindingType.TextureRemapList)
        dpg.delete_item(remap_list, children_only=True)
        dpg.push_container_stack(remap_list)

        try:
            for label, imglist in dict_of_lists.items():
                if self.texremap_not_empty and not len(imglist): continue # hide empty

                with dpg.tree_node(label=f"{label:8s} ({len(imglist)} entries)",
                                   default_open=True) as node:
                    gui_utils.populate_imglist(node,imglist,target_len)

                dpg.add_separator()

        finally:
            dpg.pop_container_stack()

###################################### AppActions ##############################
class AppActions:
    def __init__(self,app,view):
        self.app = app
        self.view = view

        with dpg.handler_registry() as global_handler:
            dpg.add_mouse_down_handler(callback=self.on_mouse_down)
            dpg.add_mouse_release_handler(callback=self.on_mouse_up)
            dpg.add_mouse_click_handler(callback=self.on_mouse_click)
            dpg.add_mouse_double_click_handler(callback=self.on_mouse_dblclick)
            dpg.add_mouse_wheel_handler(callback=self.on_mouse_wheel)
            dpg.add_mouse_move_handler(callback=self.on_mouse_move)
            dpg.add_mouse_drag_handler(callback=self.on_mouse_drag)

    ### GUI callbacks that opens a file dialog ###
    def show_file_dialog(self, type:BindingType, init_path=None, init_filename=None):
        dlg = self.view.get_dpg_item(type)
        kwargs = {}
        if init_path: kwargs["default_path"] = init_path
        if init_filename: kwargs["default_filename"] = init_filename
        
        dpg.configure_item(dlg, **kwargs)
        dpg.show_item(dlg)

    ### File load/save/export ###
    def open_bsp_file(self, bsppath:str|Path=None): # dialog callback
        ''' load bsp, then load wadstats '''
        if not bsppath:
            self.show_file_dialog(BindingType.BspOpenFileDialog)
            return 
        self.app.data.load_bsp(bsppath)

    def reload(self, *_): # menu callback
        if self.app.data.bsppath:
            self.app.data.load_bsp(self.app.data.bsppath)

    def save_bsp_file(self, backup:bool=None, confirm=None):
        if not backup:
            pass #TODO: confirm
        
    def save_bsp_file_as(self, bsppath:str|Path=None, confirm=None):
        if not bsppath:
            try:
                def_path = self.app.data.bsppath
                init_path = def_path.parent
                init_filename = def_path.with_name(def_path.stem + "_output.bsp")
            except:
                init_path, init_filename = None, None
                
            self.show_file_dialog(BindingType.BspSaveFileDialog)
            return 
            
        elif Path(bsppath).exists() and not confirm:
            return # show confirmation dialog
        # todo: save file
        
    def load_mat_file(self, matpath:str|Path=None): # dialog callback
        if not matpath:
            self.show_file_dialog(BindingType.MatLoadFileDialog)
            return 
        self.app.data.load_materials(matpath)

    def export_custommat(self, outpath:str|Path=None, confirm=None):
        if not outpath:
            try:
                def_path = bsp_custommat_path(self.app.data.bsppath)
                init_path = def_path.parent
                init_filename = def_path.with_name(def_path.stem + "_output.bsp")
            except:
                init_path, init_filename = None, None
                
            self.show_file_dialog(BindingType.MatExportFileDialog)
            return 
            
        elif outpath.exists() and not confirm:
            return # show confirmation dialog
        
        dump_texinfo(self.app.data.bsppath,0b1110000000000, None,
                     material_set=self.app.data.wannabe_set,
                     outpath=Path(app_data["file_path_name"]))


    ## wad selection callback
    def load_selected_wads(self, *_): # button callback
        # TODO: use self.view.wad_found_paths as the only source of truth please
        selection_paths = tuple(x.path for x in self.view.wadstats if x.selected)
        self.view.load_external_wad_textures(selection_paths)

    ## Gallery actions
    def select_all_textures(self, sender, app_data, value:bool=False):
        log.debug(f"selection: {value}")
        for item in self.view.gallery.data: # only the list in gallery data is selectable
            item._select_cb(sender,value)
    def selection_set_material(self, sender, app_data, mat:str):
        for item in self.view.gallery.data:
            if item.selected:
                item.mat = mat
    def selection_embed(self, sender, app_data, embed:bool):
        for item in self.view.gallery.data:
            if item.selected:
                item.become_external = not embed

    ## file drop
    def handle_drop(self, data, keys): # DearPyGui_DragAndDrop
        if not isinstance(data, list): return
        suffix = Path(data[0]).suffix.lower()
        if suffix == ".bsp":
            self.app.data.load_bsp(data[0])
        elif suffix == ".txt":
            self.app.data.load_materials(data[0])

    ### GLOBAL IO handlers ###
    def on_mouse_x(self,cbname,sender,data):
        try: self._mouse_callbacks[cbname](data)
        except (AttributeError, KeyError): pass
    def on_mouse_down (self,sender,data): self.on_mouse_x("mouse_down", sender,data)
    def on_mouse_up   (self,sender,data): self.on_mouse_x("mouse_up",   sender,data)
    def on_mouse_click(self,sender,data): self.on_mouse_x("mouse_click",sender,data)
    def on_mouse_dblclick(self,sender,data): self.on_mouse_x("mouse_dblclick",sender,data)
    def on_mouse_wheel(self,sender,data): self.on_mouse_x("mouse_wheel",sender,data)
    def on_mouse_move (self,sender,data): self.on_mouse_x("mouse_move", sender,data)
    def on_mouse_drag (self,sender,data): self.on_mouse_x("mouse_drag", sender,data)

    def set_mouse_event_target(self,sender=None,callbacks=None):
        ''' on hover, call this to send the mouse event over to the callbacks
            since this is a continuous process, we set a frame callback on the
            next frame to clear everything
        '''
        self._mouse_event_target = sender
        self._mouse_callbacks = callbacks
        ## clear on next frame
        dpg.set_frame_callback(dpg.get_frame_count()+1,
                               lambda: self.set_mouse_event_target())


class App:
    def __init__(self):
        self.data = AppModel(self)
        self.view = AppView(self)
        self.do = AppActions(self,self.view)
        dpg.set_frame_callback(1,callback=lambda:self.view.set_viewport_ready())

        TextureView.class_init(app=self,
                               mat_update_cb=self.view.update_wannabe_material_tables,
                               mouse_event_registrar=self.do.set_mouse_event_target)
                               
    def load_config(self,cfgpath):
        pass

    def update(self,*args,**kwargs):
        ''' pass this to self.view.update '''
        return self.view.update(*args,**kwargs)

