''' combined model+controller for the GUI app
    model being the dataclass
    controller being its methods
'''
from .mappings import *
from .textureview import TextureView
from .galleryview import GalleryView
from .. import consts
from ..enums import MaterialEnum
from ..common import search_materials_file
from ..bsputil import wadlist, guess_lumpenum
from ..materials import MaterialSet, TextureRemapper
from jankbsp import BspFileBasic as BspFile
from jankbsp.types import EntityList
from pathlib import Path
from dataclasses import dataclass, field, asdict
from operator import attrgetter
import dearpygui.dearpygui as dpg
import re

def _debugitem(tag):
    print("CONFIG: ", dpg.get_item_configuration(tag))
    print("INFO:   ", dpg.get_item_info(tag))
    print("STATE:  ", dpg.get_item_state(tag))
    print("VALUE:  ", dpg.get_value(tag))
    print()

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

    def _fmt(self):
        parts = None
        if self.found is not None:
            parts = [self._found_str[self.found], self._loaded_str[self.loaded]]
            parts = list(filter(lambda x:len(x),parts))
        return " ".join([self.name, f"({', '.join(parts)})" if parts else ""])

    def __post_init__(self):
        callback = lambda s,a,u: setattr(self,"selected",dpg.get_value(s))
        self.uuid = dpg.add_selectable(label=self._fmt(),
                                       parent=target["grpWadlist"],
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
    # dpg : any # reference to the dearpygui module

    # primary data
    bsppath : str           = None
    bsp     : BspFile       = None
    matpath : str           = None
    mat_set : MaterialSet   = field(default_factory=MaterialSet)
    wannabe_set:MaterialSet = field(default_factory=MaterialSet)

    # name, found, loaded, selected
    wadstats: list[WadStatus] = field(default_factory=list)

    gallery_view : GalleryView = field(default_factory=GalleryView)

    # view settings
    _viewport_ready=False

    gallery_size_val = 1 # full size. refer to gallery_view_map
    texview_show = [0]
    matchars = MaterialSet.MATCHARS # edit if loading CZ/CZDS
    filter_matchars = matchars
    filter_matnames = ""
    _filter_matchars = matchars
    _filter_matnames = ""
    # set that holds tags of togglers to update their values
    togglers : set      = field(default_factory=lambda:set())
    # set that holds tags of labelled items to format their labels
    formattables : set  = field(default_factory=lambda:set())
    # holds the original format of the labels
    formattables_raw : dict = field(default_factory=lambda:{})

    # settings
    auto_load_materials=True # try find materials.path
    auto_load_wads=True # try find wads
    insert_remap_entity=False
    backup=True # creates backup file if saving in same file

    @property
    def filter_matname_list(self):
        return re.split("\s", self.filter_matnames)

    @property
    def gallery_size_text(self):
        return gallery_size_map[self.gallery_size_val][0]
    @gallery_size_text.setter
    def gallery_size_text(self,value):
        item = next((x for x in gallery_size_map if x[0]==value), None)
        if item:
            self.gallery_size_val = gallery_size_map.index(item)
            self.gallery_view.render()
    @property
    def filter_matchars(self):
        return self._filter_matchars
    @filter_matchars.setter
    def filter_matchars(self,value):
        self._filter_matchars = value
        self.do_filter_mat_entries()
    @property
    def filter_matnames(self):
        return self._filter_matnames
    @filter_matnames.setter
    def filter_matnames(self,value):
        self._filter_matnames = value
        self.do_filter_mat_entries()

    def insert_bindings(self,show=False):
        ''' inserts hidden controls that are linked to this entity
            this provides a single source of truth between the model and the view
            other controls can reference these controls with the "source" property
            and update the model by setting callback to app.update
        '''
        _bf = BindingFlag # shorthand
        with dpg.window(tag="app_bindings",show=show):
            for input_type,prop,data,flags in bindings:
                tag = "app:" + prop
                dpg_method = getattr(dpg, f"add_{input_type}")
                init_val = getattr(self,prop) & data if _bf.Flag in flags \
                        else getattr(self,prop)

                if _bf.ListValues in flags:
                    dpg_method(data,tag=tag,label=prop,default_value=init_val)
                else:
                    dpg_method(     tag=tag,label=prop,default_value=init_val)

    def update(self,*args):
        ''' this is called by the gui when it updates a prop linked to the model
        '''
        if self.reflecting: return
        _bf = BindingFlag # shorthand

        for _,prop,data,flags in bindings:
            if _bf.ReadOnly in flags: continue # don't update these
            tag = "app:" + prop
            val = dpg.get_value(tag)

            if _bf.Flag in flags and val:
                setattr(self, prop, getattr(self,prop) | data)
            elif _bf.Flag in flags and not val:
                setattr(self, prop, getattr(self,prop) & ~data)
            else:
                setattr(self, prop, val)

        self.reflect()

    def reflect(self):
        ''' updates the gui to reflect model values '''
        if not self._viewport_ready: return
        self.reflecting = True

        if self.bsppath:
            dpg.set_viewport_title(f"{self.bsppath} - BspTexRemap GUI")
        else:
            dpg.set_viewport_title("BspTexRemap GUI")

        for _,prop,data,flags in bindings:
            tag = "app:" + prop
            val = getattr(self,prop) & data \
                    if BindingFlag.Flag in flags \
                    else getattr(self,prop)
            dpg.set_value(tag,val)

        for item in self.togglers:
            source = dpg.get_item_configuration(item)["user_data"]
            dpg.set_value(item, dpg.get_value(source))

        for item in self.formattables:
            # user data contains a list/tuple of attrs to format to
            item_cfg = dpg.get_item_configuration(item)
            label, attrs = item_cfg["label"], item_cfg["user_data"]
            label = formattables_raw.setdefault(item, label) # set first time values
            attr_values = attrgetter(*attrs)(self)
            dpg.configure_item(item, label=label.format(*attr_values))

        self.reflecting = False

    def set_viewport_ready(self):
        self._viewport_ready = True
        self.reflect()

    # all the show file dialog stuff
    def do_show_open_file(self, sender, app_data):
        dpg.show_item(target["dlgBspFileOpen"])
    def do_show_save_file_as(self, sender, app_data):
        dpg.show_item(target["dlgBspFileSaveAs"])
    def do_show_open_mat_file(self, sender, app_data):
        dpg.show_item(target["dlgMatFileOpen"])
    def do_show_save_mat_file(self, sender, app_data):
        dpg.show_item(target["dlgMatFileExport"])


    def do_open_file(self, sender, app_data):
        self.load_bsp(app_data["file_path_name"])

    def do_reload(self, sender, app_data):
        if self.bsppath: self.load_bsp(self.bsppath)
    def do_save_file(self, sender, app_data): pass
    def do_save_file_as(self, sender, app_data): pass
    def do_load_mat_file(self, sender, app_data):
        self.load_materials(app_data["file_path_name"])

    def do_export_custommat(self, sender, app_data): pass

    def do_drop(self, data, keys): # DearPyGui_DragAndDrop
        if not isinstance(data, list): return
        suffix = Path(data[0]).suffix.lower()
        if suffix == ".bsp":
            self.load_bsp(data[0])
        elif suffix == ".txt":
            self.load_materials(data[0])

    def do_filter_mat_entries(self,*args):
        def matfilter(mat):
            return mat.upper() in self._filter_matchars.upper() \
                    if len(self._filter_matchars) else True
        def namefilter(name):
            if not len(self._filter_matnames): return True
            fragment = self._filter_matnames.split(" ")
            found = [" " if f.upper() in name.upper() else ""  for f in fragment]
            return len("".join(found))

        for row in dpg.get_item_children(target["tblMatEntries"],1):
            mat = dpg.get_value(dpg.get_item_children(row,1)[0])
            name = dpg.get_value(dpg.get_item_children(row,1)[1])
            
            if matfilter(mat):
                if namefilter(name):
                    dpg.configure_item(row,show=True)
                    continue
            dpg.configure_item(row,show=False)



    def load_bsp(self, bsppath):
        self.bsppath = bsppath
        with open(self.bsppath, "rb") as f:
            self.bsp = BspFile(f, lump_enum=guess_lumpenum(self.bsppath))

        self.load_textures(self.bsp.textures)

        if self.auto_load_materials:
            matpath = search_materials_file(self.bsppath)
            if matpath:
                self.load_materials(matpath)

        print(wadlist(self.bsp.entities,True))
        self.wadstats = [WadStatus(w) for w in wadlist(self.bsp.entities,True)]
        self.reflect()

    def load_textures(self,miptexes,update=False):
        if update:
            old_list = self.gallery_view.data
            for newtex in miptexes:
                finder = lambda tex:tex.name.lower() == newtex.name.lower()
                oldtex = next(filter(finder,old_list),None)
                if oldtex:
                    oldtex.update_miptex(newtex)
                # else:
                #     old_list.append(TextureView.from_miptex(newtex))
        else:
            self.gallery_view.data = [TextureView.from_miptex(item) \
                    for item in miptexes]
        if self._viewport_ready: self.gallery_view.render()

    def load_materials(self, matpath):
        self.matpath = matpath
        self.mat_set = MaterialSet.from_materials_file(self.matpath)
        self.reflect()
        self.render_material_tables()

    def render_material_tables(self):
        choice_set = self.mat_set.choice_cut()
        avail_colors = lambda n: (0,255,0) if n else (255,0,0)
        is_suitable = lambda name: \
                consts.MATNAME_MIN_LEN <= len(name) <= consts.MATNAME_MAX_LEN
        suitable_mark = lambda name: "Y" if is_suitable(name) else "N"
        suitable_colors = lambda name: (0,255,0) if is_suitable(name) else (255,0,0)

        # SUMMARY TABLE
        dpg.delete_item(target["tblMatSummary"], children_only=True)
        dpg.push_container_stack(target["tblMatSummary"])

        weights = [0.4,1.8,1,1]
        for i, label in enumerate(("","Material","Count","Usable")):
            dpg.add_table_column(label=label,init_width_or_weight=weights[i])

        for mat in self.mat_set.MATCHARS:
            with dpg.table_row():
                dpg.add_text(MaterialEnum(mat).value)
                dpg.add_text(MaterialEnum(mat).name)
                dpg.add_text(len(self.mat_set[mat]))
                dpg.add_text(
                        len(choice_set[mat]),
                        color=avail_colors(len(choice_set[mat]))
                )
        with dpg.table_row(): # totals row
            dpg.add_text("")
            dpg.add_text("TOTAL")
            dpg.add_text(len(self.mat_set))
            dpg.add_text(len(choice_set))

        dpg.pop_container_stack()

        # ENTRIES TABLE
        dpg.delete_item(target["tblMatEntries"], children_only=True)
        dpg.push_container_stack(target["tblMatEntries"])

        weights = [0.4,3,1]
        for i, label in enumerate(("Mat","Name","Usable")):
            dpg.add_table_column(label=label,init_width_or_weight=weights[i])

        for mat in self.filter_matchars:
            if mat not in self.mat_set.MATCHARS: continue
            for name in self.mat_set[mat]:
                with dpg.table_row():
                    dpg.add_text(mat)
                    dpg.add_text(name)
                    dpg.add_text(suitable_mark(name),color=suitable_colors(name))

        dpg.pop_container_stack()

    def render_wadstats(self):
        dpg.delete_item(target["grpWadlist"], children_only=True)
        dpg.push_container_stack(target["grpWadlist"])


