''' combined model+controller for the GUI app
    model being the dataclass
    controller being its methods

    TODO: REDO BINDINGS
    list and radio buttons don't share source
    have a dict with key=tag and value=prop
'''
from . import mappings # proper way
from .mappings import BindingType, RemapEntityActions
from .textureview import TextureView
from .galleryview import GalleryView
from . import gui_utils
from .. import consts, utils
from ..enums import MaterialEnum
from ..common import search_materials_file, search_wads, filter_materials
from ..bsputil import wadlist, guess_lumpenum
from ..materials import MaterialSet, TextureRemapper
from jankbsp import BspFileBasic as BspFile
from jankbsp.types import EntityList
from pathlib import Path
from dataclasses import dataclass, field, asdict
from operator import attrgetter
from collections import namedtuple
from typing import NamedTuple, ClassVar
import dearpygui.dearpygui as dpg
import re, logging

log = logging.getLogger(__name__)
def _debugitem(tag):
    log.debug("CONFIG: {!r}", dpg.get_item_configuration(tag))
    log.debug("INFO:   {!r}", dpg.get_item_info(tag))
    log.debug("STATE:  {!r}", dpg.get_item_state(tag))
    log.debug("VALUE:  {!r}", dpg.get_value(tag))
    log.debug()

@dataclass
class WadStatus:
    #app: any # reference to app
    name : str
    found : bool = None
    loaded : bool = False
    selected : bool = False
    uuid : any = None
    _found_str = {True:"found",False:"not found"}
    _loaded_str = {True:"loaded",False:""}
    _parent: ClassVar = None

    def _fmt(self):
        parts = None
        if self.found is not None:
            parts = [self._found_str[self.found], self._loaded_str[self.loaded]]
            parts = list(filter(lambda x:len(x),parts))
        return " ".join([self.name, f"({', '.join(parts)})" if parts else ""])

    def __post_init__(self):
        callback = lambda s,a,u: setattr(self,"selected",dpg.get_value(s))
        self.uuid = dpg.add_selectable(label=self._fmt(),
                                       parent=self._parent,
                                       disable_popup_close=True,
                                       callback=callback)

    def __del__(self):
        if self.uuid: dpg.delete_item(self.uuid)

    def update(self, found=None, loaded=None):
        if found is not None: self.found = found
        if loaded: self.loaded = loaded
        dpg.configure_item(self.uuid,
                           label=self._fmt(),
                           enabled=False if self.found is False else True)


@dataclass
class AppModel:
    app : any # reference to app
    # primary data
    bsppath : str     = None
    bsp     : BspFile = None
    matpath : str     = None
    mat_set : MaterialSet     = field(default_factory=MaterialSet)
    wannabe_set : MaterialSet = field(default_factory=MaterialSet)

    matchars : str    = MaterialSet.MATCHARS # edit if loading CZ/CZDS

    # settings
    auto_load_materials : bool = True # try find materials.path
    auto_load_wads      : bool = True # try find wads
    remap_entity_action : RemapEntityActions = RemapEntityActions.Insert
    backup              : bool = True # creates backup file if saving in same file

    def load_bsp(self, bsppath):
        self.bsppath = bsppath
        with open(self.bsppath, "rb") as f:
            self.bsp = BspFile(f, lump_enum=guess_lumpenum(self.bsppath))

        self.app.view.load_textures(self.bsp.textures)

        if self.auto_load_materials:
            matpath = search_materials_file(self.bsppath)
            if matpath:
                self.load_materials(matpath)

        self.app.view.update_wadlist()

    def load_materials(self, matpath):
        self.matpath = matpath
        self.mat_set = MaterialSet.from_materials_file(self.matpath)
        self.app.view.reflect()
        self.app.do.render_material_tables()



@dataclass(frozen=True)
class BindingEntry:
    type: BindingType
    prop: namedtuple = None
    data: any = None

@dataclass
class AppView:
    # the parent app
    app : any
    # dict of bound items
    bound_items : dict           = field(default_factory=dict)

    # list of wadstatus
    wadstats: list[WadStatus]    = field(default_factory=list)
    # all textures in the bsp
    textures : list[TextureView] = field(default_factory=list)
    # gallery view (only store the filtered items in its data)
    gallery : GalleryView        = field(default_factory=GalleryView)

    # check against issuing dpg commands when viewport isn't ready
    _viewport_ready : bool       = False

    # material entry filter settings
    filter_matchars : str        = ""
    filter_matnames : str        = ""

    # texture gallery view settings
    gallery_show_val : int       = 2 # all  -> mappings.gallery_show_map
    gallery_size_val : int       = 1 # full -> mappings.gallery_size_map
    filter_str : str             = ""
    filter_unassigned : bool     = False # show only textures without materials
    filter_radiosity : bool      = False # hide radiosity generated textures
    selection_mode : bool        = False

    def bind(self, tag, type:BindingType, prop=None, data=None):
        ''' binds the tag to the prop 
            prop is a tuple of obj and propname. 
            - get value using getattr(*prop)
            - set value using setattr(*prop, value)
            data is usually passed by value
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
        
        if item.type == BindingType.Value:
            setattr(*item.prop, app_data)
        elif item.type == BindingType.ValueIs:
            setattr(*item.prop, item.data)
        elif item.type == BindingType.TextMappedValue:
            val = self._index_of(item.data,lambda x:x == app_data)
            if val is not None: setattr(*item.prop, val)

        # updates other bound items with same prop
        self.reflect(not_tagged=sender,
                     prop=item.prop,
                     types=mappings.reflect_all_binding_types)

        # update some other things based on prop
        if item.prop[0] == self and item.prop[1] in \
        ["gallery_show_val", "filter_str", "filter_unassigned", "filter_radiosity"]:
            self.update_gallery()
        elif tuple(item.prop) == (self,"gallery_size_val"):
            self.update_gallery(size_only=True)


    def reflect(self, not_tagged=None, prop=None, types=mappings.reflect_all_binding_types):
        ''' updates all bound items (optionally of given prop) 
            prop is a tuple of obj and propname. 
            - get value using getattr(*prop)
        '''
        for tag,item in self.bound_items.items():
            if tag == not_tagged: continue
            if prop and item.prop != prop: continue
            if item.type not in types: continue

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
        self.reflect(types=mappings.reflect_all_binding_types)
        self.update_gallery()

    def load_textures(self, miptexes, update=False):
        if update:
            old_list = self.textures
            for newtex in miptexes:
                finder = lambda tex:tex.name.lower() == newtex.name.lower()
                oldtex = next(filter(finder,old_list),None)
                if oldtex:
                    oldtex.update_miptex(newtex)
                # else:
                #     old_list.append(TextureView.from_miptex(newtex))
        else:
            self.textures = [TextureView.from_miptex(item) for item in miptexes]
        if self._viewport_ready: self.update_gallery()

    def update_wadlist(self):
        WadStatus._parent = self.get_dpg_item(type=BindingType.WadListGroup)
        wads = wadlist(self.app.data.bsp.entities,True)
        self.wadstats = [WadStatus(w) for w in wads]
        
        wad_paths = search_wads(self.app.data.bsppath, wads)
        for item in self.wadstats:
            item.update(found=bool(wad_paths[item.name]))

        #_propbind = namedtuple("PropertyBinding",["obj","prop"])
        self.reflect() #prop=_propbind(self, "wadstats"))

    def update_gallery(self, size_only=False):
        ''' filters the textures list, then passes it off to gallery to render '''
        # all the filters in modelcontroller assembled
        log.debug("updating gallery")
        f_a = mappings.gallery_show_map[self.gallery_show_val].filter_fn
        f_u = lambda item: MaterialSet.strip(item.name) not in self.app.data.mat_set
        f_r = lambda item: not item.name.lower().startswith("__rad")
        f_s = lambda item: utils.filterstring_to_filter(self.filter_str)(item.name)
        
        if not size_only:
            # assemble the filter stack
            the_list = filter(f_a,self.textures)
            if self.filter_unassigned:
                the_list = filter(f_u, the_list)
            if self.filter_radiosity:
                the_list = filter(f_r, the_list)
            if self.filter_str:
                the_list = filter(f_s, the_list)
            # finally filter and send it to gallery
            self.gallery.data = list(the_list)
        
        # set gallery scale
        size_tuple = mappings.gallery_size_map[self.gallery_size_val]
        log.debug(size_tuple)
        self.gallery.scale = size_tuple.scale
        self.gallery.max_width = size_tuple.max_width
        
        # render the gallery
        self.gallery.render()
    
class AppActions:
    def __init__(self,app,view):
        self.app = app
        self.view = view

    def show_open_file(self, *_):
        dpg.show_item(self.view.get_dpg_item(type=BindingType.BspOpenFileDialog))
    def show_save_file_as(self, *_):
        dpg.show_item(self.view.get_dpg_item(type=BindingType.BspSaveFileDialog))
    def show_open_mat_file(self, *_):
        dpg.show_item(self.view.get_dpg_item(type=BindingType.MatLoadFileDialog))
    def show_save_mat_file(self, *_):
        dpg.show_item(self.view.get_dpg_item(type=BindingType.MatExportFileDialog))

    def open_file(self, sender, app_data):
        ''' called by the open file dialog
            load bsp, then load wadstats 
        '''
        self.app.data.load_bsp(app_data["file_path_name"])
        
    def reload(self, sender, app_data):
        if self.app.data.bsppath:
            self.app.data.load_bsp(self.app.data.bsppath)

    def save_file(self, sender, app_data): pass
    def save_file_as(self, sender, app_data): pass
    def load_mat_file(self, sender, app_data):
        self.app.data.load_materials(app_data["file_path_name"])

    def export_custommat(self, sender, app_data): pass
    
    def load_selected_wads(self, *_): pass
    def select_textures(self, sender, app_data, user_data): pass
    def selection_set_material(self, sender, app_data, user_data): pass
    def selection_embed(self, sender, app_data, user_data): pass

    def handle_drop(self, data, keys): # DearPyGui_DragAndDrop
        if not isinstance(data, list): return
        suffix = Path(data[0]).suffix.lower()
        if suffix == ".bsp":
            self.app.data.load_bsp(data[0])
        elif suffix == ".txt":
            self.app.data.load_materials(data[0])


    def render_material_tables(self):
        ME = MaterialEnum
        mat_set = self.app.data.mat_set
        choice_set = mat_set.choice_cut()

        avail_colors = lambda n: (0,255,0) if n else (255,0,0)
        is_suitable = lambda name: \
                consts.MATNAME_MIN_LEN <= len(name) <= consts.MATNAME_MAX_LEN
        suitable_mark = lambda name: "Y" if is_suitable(name) else "N"
        suitable_colors = lambda name: (0,255,0) if is_suitable(name) else (255,0,0)

        # SUMMARY TABLE
        header = (("",0.4), ("Material",1.8), "Count", "Usable")
        data = []
        for mat in mat_set.MATCHARS:
            data.append([ME(mat).value,
                         ME(mat).name,
                         len(mat_set[mat]),
                         (len(choice_set[mat]), {
                            "color" : avail_colors(len(choice_set[mat]))
                         }) ])
        data.append(["", "TOTAL", len(mat_set), len(choice_set)]) # totals row

        table = self.view.get_dpg_item(type=BindingType.MaterialSummaryTable)
        gui_utils.populate_table(table, header, data)

        # ENTRIES TABLE
        header = (("Mat",0.4), ("Name",3), "Usable")
        data = []
        for mat in self.app.data.matchars:
            for name in mat_set[mat]:
                data.append([mat, name,
                             (suitable_mark(name), {"color":suitable_colors(name)})])
        table = self.view.get_dpg_item(type=BindingType.MaterialEntriesTable)
        gui_utils.populate_table(table, header, data)


class App:
    def __init__(self):
        self.data = AppModel(self)
        self.view = AppView(self)
        self.do = AppActions(self,self.view)
        dpg.set_frame_callback(1,callback=lambda:self.view.set_viewport_ready())

    def update(self,*args,**kwargs):
        ''' pass this to self.view.update '''
        return self.view.update(*args,**kwargs)

