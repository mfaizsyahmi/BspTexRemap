''' combined model+controller for the GUI app
    model being the dataclass
    controller being its methods
'''
from .mappings import target, bindings, gallery_view_map
from .textureview import TextureView
from .galleryview import GalleryView
from ..enums import MaterialEnum
from ..common import search_materials_file
from ..bsputil import wadlist
from ..materials import MaterialSet, TextureRemapper
from jankbsp import BspFileBasic as BspFile
from jankbsp.types import EntityList
from pathlib import Path
from dataclasses import dataclass, field

@dataclass
class AppModel:
    dpg : any # reference to the dearpygui module

    # primary data
    bsppath : str           = None
    bsp     : BspFile       = None
    matpath : str           = None
    mat_set : MaterialSet   = field(default_factory=MaterialSet)

    gallery_view : GalleryView = field(default_factory=GalleryView)

    # view settings
    gallery_view_opt = 1 # full size. refer to gallery_view_map
    texview_show = [0]
    matchars = MaterialSet.MATCHARS # edit if loading CZ/CZDS
    # set that hods tags of togglers to update their values
    togglers : set = field(default_factory=lambda:set())
    _viewport_ready=False

    # settings
    auto_load_materials=True # try find materials.path
    auto_load_wads=True # try find wads
    insert_remap_entity=False
    backup=True # creates backup file if saving in same file

    def insert_bindings(self,show=False):
        ''' inserts hidden controls that are linked to this entity
            this provides a single source of truth between the model and the view
            other controls can reference these controls with the "source" property
            and update the model by setting callback to app.update
        '''
        with self.dpg.window(tag="app_bindings",show=show):
            for input_type,prop,flag,readonly in bindings:
                tag = "app:" + prop
                getattr(self.dpg, f"add_{input_type}")(
                        tag=tag,
                        label=prop,
                        default_value = getattr(self,prop) & flag if flag \
                                else getattr(self,prop)
                )

    def update(self,*args):
        ''' this is called by the gui when it updates a prop linked to the model
        '''
        if self.reflecting: return
        for _,prop,flag,readonly in bindings:
            if readonly: continue # don't update these
            tag = "app:" + prop
            val = self.dpg.get_value(tag)
            if flag and val:
                setattr(self, prop, getattr(self,prop) | flag)
            elif flag and not val:
                setattr(self, prop, getattr(self,prop) & ~flag)
            else:
                setattr(self, prop, val)
        self.reflect()

    def reflect(self):
        ''' updates the gui to reflect model values '''
        if not self._viewport_ready: return
        self.reflecting = True

        if self.bsppath:
            self.dpg.set_viewport_title(f"{self.bsppath} - BspTexRemap GUI")
        else:
            self.dpg.set_viewport_title("BspTexRemap GUI")

        for _,prop,flag,readonly in bindings:
            tag = "app:" + prop
            val = getattr(self,prop) & flag if flag else getattr(self,prop)
            self.dpg.set_value(tag,val)

        for toggler in self.togglers:
            source = self.dpg.get_item_configuration(toggler)["user_data"]
            self.dpg.set_value(toggler, self.dpg.get_value(source))

        self.reflecting = False

    def set_viewport_ready(self):
        self._viewport_ready = True
        self.reflect()

    # all the show file dialog stuff
    def do_show_open_file(self, sender, app_data):
        self.dpg.show_item(target["dlgBspFileOpen"])
    def do_show_save_file_as(self, sender, app_data):
        self.dpg.show_item(target["dlgBspFileSaveAs"])
    def do_show_open_mat_file(self, sender, app_data):
        self.dpg.show_item(target["dlgMatFileOpen"])
    def do_show_save_mat_file(self, sender, app_data):
        self.dpg.show_item(target["dlgMatFileExport"])


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
        if isinstance(data, list):
            self.load_bsp(data[0])

    def load_bsp(self, bsppath):
        self.bsppath = bsppath
        with open(self.bsppath, "rb") as f:
            self.bsp = BspFile(f)

        self.gallery_view.data = [TextureView.from_miptex(item) \
                for item in self.bsp.textures]
        if self._viewport_ready: self.gallery_view.render()

        if self.auto_load_materials:
            matpath = search_materials_file(self.bsppath)
            if matpath:
                self.load_materials(matpath)

    def load_materials(self, matpath):
        self.matpath = matpath
        self.mat_set = MaterialSet.from_materials_file(self.matpath)
        self.reflect()
        self.render_material_summary()

    def render_material_summary(self):
        choice_set = self.mat_set.choice_cut()
        avail_colors = lambda n: (0,255,0) if n else (255,0,0)

        self.dpg.delete_item(target["tblMatSummary"], children_only=True)
        self.dpg.push_container_stack(target["tblMatSummary"])

        weights = [0.4,1.8,1,1]
        for i, label in enumerate(("","Material","Total","Usable")):
            self.dpg.add_table_column(label=label,init_width_or_weight=weights[i])

        for mat in self.mat_set.MATCHARS:
            with self.dpg.table_row():
                self.dpg.add_text(MaterialEnum(mat).value)
                self.dpg.add_text(MaterialEnum(mat).name)
                self.dpg.add_text(len(self.mat_set[mat]))
                self.dpg.add_text(
                        len(choice_set[mat]),
                        color=avail_colors(len(choice_set[mat]))
                )
        with self.dpg.table_row(): # totals row
            self.dpg.add_text("")
            self.dpg.add_text("TOTAL")
            self.dpg.add_text(len(self.mat_set))
            self.dpg.add_text(len(choice_set))

        self.dpg.pop_container_stack()
