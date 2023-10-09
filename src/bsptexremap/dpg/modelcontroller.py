''' MVC for the GUI app
'''
import dearpygui.dearpygui as dpg

from jankbsp import BspFileBasic, WadFile
from jankbsp.types import EntityList
from jankbsp.types.wad import WadMipTex

from .. import utils
from ..enums import MaterialEnum, DumpTexInfoParts
from ..common import * # This inserts consts, so must come before .consts!!!
from ..utils import failure_returns_none
from ..bsputil import wadlist, guess_lumpenum, bsp_custommat_path
from ..materials import MaterialSet, TextureRemapper

from . import consts, mappings, gui_utils
from .mappings import BindingType, RemapEntityActions
from .wadstatus import WadStatus, WadList
from .textureview import TextureView
from .galleryview import GalleryView
from .dbgtools import *
from .colors import MaterialColors
from .pickleddict import PickledDict

from pathlib import Path
from dataclasses import dataclass, field #, asdict
from collections import namedtuple, UserDict
from typing import NamedTuple, ClassVar
from operator import attrgetter
from itertools import chain
from concurrent.futures import ThreadPoolExecutor
from math import log10, ceil
import re, logging, json, tomllib

log = logging.getLogger(__name__)
BspFile = BspFileBasic

@dataclass
class AppModel:
    app : any # reference to app
    # primary data
    bsppath : Path    = None
    bsp     : BspFile = None
    matpath : Path    = None
    mat_set      : MaterialSet = field(default_factory=MaterialSet)
    wannabe_set  : MaterialSet = field(default_factory=MaterialSet)
    direct_remap : dict        = field(default_factory=dict)

    # settings
    auto_load_materials : bool = True # try find materials.path
    auto_load_wads      : bool = True # try find wads
    auto_load_wannabes  : bool = True # parse entity
    allow_unembed       : bool = False
    remap_entity_action : int  = 0    # RemapEntityActions.Insert
    backup              : bool = True # creates backup file if saving in same file
    show_summary        : bool = False # summary window after edits

    # info (generally read-only from other places)
    remap_entity_count  : int  = 0
    matchars : str    = MaterialSet.MATCHARS # edit if loading OF/CZ/CZ/DS        

    def load_bsp(self, bsppath):
        ''' loads given bsp, and kickstarts some post-load operations
            (has side effects)
        '''
        log.info(f"Loading BSP: {bsppath!s}")
        gui_utils.show_loading(True)

        ## load bsp
        self.bsppath = Path(bsppath)
        with open(self.bsppath, "rb") as f:
            self.bsp = BspFile(f, lump_enum=guess_lumpenum(self.bsppath))

        ## reset all the matchars
        self.matchars = matchars_by_mod(bsp_modname_from_path(self.bsppath))
        MaterialSet.MATCHARS = self.matchars
        TextureView.class_set_matchars(self.matchars)

        ## load textures
        self.app.view.load_textures(self.bsp.textures)

        ## setup material set
        self.matpath = None
        if self.auto_load_materials:
            matpath = search_materials_file(self.bsppath)
            if matpath:
                self.load_materials(matpath) # sets self.matpath and render the tables
        self.app.view.render_material_tables() # manually render tables

        ## setup wannabe set & direct remaps
        self.wannabe_set = MaterialSet()
        self.direct_remap = {}
        self.remap_entity_count = 0

        for texremap_ent in iter_texremap_entities(self.bsp.entities):
            self.remap_entity_count += 1
            if self.auto_load_wannabes:
                self.wannabe_set |= MaterialSet.from_entity(texremap_ent)

        def_path = bsp_custommat_path(self.app.data.bsppath)
        if self.auto_load_wannabes and def_path.exists():
            self.wannabe_set |= MaterialSet.from_materials_file(def_path)
            self.app.view.update_gallery_items()

        self.app.view.update_wannabe_material_tables()

        ## setup wad
        self.app.view.update_wadlist() # populates wadstats list
        if self.auto_load_wads:
            entries = {x.order: x.path for x in self.app.view.wadstats if x.path}
            self.app.view.load_external_wad_textures(entries)

        log.info("Done.")
        gui_utils.show_loading(False)


    def parse_remap_entities(self):
        if not self.bsp: return
        for texremap_ent in iter_texremap_entities(self.bsp.entities):
            self.wannabe_set |= MaterialSet.from_entity(texremap_ent)

    def load_materials(self, matpath):
        self.matpath = Path(matpath)
        self.mat_set = MaterialSet.from_materials_file(self.matpath)
        self.app.view.reflect()
        self.app.view.render_material_tables()

    def load_wannabes(self, matpath):
        # load the set from file
        wannabes = MaterialSet.from_materials_file(matpath)
        # merge with set in appdata
        self.wannabe_set |= wannabes
        # update remap view
        self.app.view.reflect()
        self.app.view.update_wannabe_material_tables()

        # force textures in the entries to be embedded
        # which requires we know which wads are loaded during export
        # TODO: move to a subroutine toggleable under a config
        '''
        wads = re.match(r"(?im)(?:^// wads:).*$", Path(matpath).read_text())
        if wads:
            wadlist = wads.split(",")
            for wad_stat in self.app.view.wadstats:
                if wad_stat.name in wadlist:
                    dpg.set_value(wad_stat.uuid,True) # become selected
            self.app.do.load_selected_wads()

        for item in self.app.view.textures:
            if item.matname in wannabes:
                item.set_embed(True)
        '''

    def TEST_load_wad(self,wadpath):
        ''' TEST of loading a wad file directly '''
        with time_it():
            log.debug(f"LOADING WAD: {Path(wadpath).name}")
            with open(wadpath, "rb") as fp:
                wad = WadFile.load(fp)
        self.app.view.load_textures([item._miptex for item in wad.entries])


    def commit_bsp_edits(self, include_report=False, show_summary=True):
        ''' returns a new bsp object with the edits applied, namely:
            1. embed/unembed textures
            2. rename textures
            3. add/remove info_texture_remap
        '''
        ###---------------------------------------------------------------------
        ### PHASE ONE - Figuring out what edits need to be done
        ###---------------------------------------------------------------------
        ## 1. texture embedding/unembedding
        # dict of name:data
        things_to_embed  = {item.name: item.external_src \
                            for item in self.app.view.textures \
                            if item.become_external==False}
        # get the names of wads with the textures
        wadnames = set((src for src in things_to_embed.values()))
        # fetch the cached miptexes and puts them into the dict
        for wadname in wadnames:
            for miptex in self.view.wad_cache[wadname]:
                if miptex.name in things_to_embed:
                    things_to_embed[miptex.name] = miptex

        things_to_unembed=[item.name for item in self.app.view.textures \
                           if item.become_external==True]

        ## 2. texture renamings
        tr = TextureRemapper(target_set = self.wannabe_set,
                             choice_set = self.mat_set.choice_cut(),
                             map_dict = self.direct_remap)

        remap_dict = {item.name:tr(item.name) for item in self.bsp.textures}
        remap_dict = {oldname:newname for oldname,newname in remap_dict.items() \
                      if newname != oldname}

        ## 3. info_texture_remap action -> RemapEntityActions enum
        info_texture_remap_action \
        = mappings.remap_entity_actions_map[self.remap_entity_action].value


        ###---------------------------------------------------------------------
        ### PHASE TWO - Load a new BspFile instance and commit the edits
        ###---------------------------------------------------------------------
        ## 0. create new BspFile instance
        with open(self.bsppath, "rb") as f:
            newbsp = BspFile(f, lump_enum=guess_lumpenum(self.bsppath))

        list_embedded = []
        list_unembedded = []
        dict_renamed = {}
        for i in range(len(newbsp.textures)):
            this_miptex = newbsp.textures[i]

            ## 1. embed/unembed
            if this_miptex.name in things_to_embed and this_miptex.is_external:
                # replace itself with the entry
                newbsp.textures[i] = things_to_embed[this_miptex.name]
                list_embedded.append(this_miptex.name)
            elif this_miptex.name in things_to_unembed and not this_miptex.is_external:
                this_miptex.unembed()
                list_unembedded.append(this_miptex.name)

            ## 2. rename
            if this_miptex.name in remap_dict:
                dict_renamed[this_miptex.name] = remap_dict[this_miptex.name]
                this_miptex.name = remap_dict[this_miptex.name]

        ## 3. entity
        oldcount = len(newbsp.entities.data)
        if info_texture_remap_action == RemapEntityActions.Insert:
            _s = MaterialSet.strip
            if (ent := next((ent for ent in newbsp.entities \
                             if ent["classname"].lower() \
                                == consts.TEXREMAP_ENTITY_CLASSNAME.lower()),\
                            None)):
                ent.update({_s(old): _s(new) for old,new in remap_dict.items()})
            else:
                newbsp.entities.data.append({
                    **{_s(old): _s(new) for old,new in remap_dict.items()},
                    "origin": "0 0 16", "angles": "90 90 0",
                    "classname" : consts.TEXREMAP_ENTITY_CLASSNAME
                })

        elif info_texture_remap_action == RemapEntityActions.Remove:
            newbsp.entities.data = [ent for ent in newbsp.entities.data \
                                    if ent["classname"].lower() \
                                       == consts.TEXREMAP_ENTITY_CLASSNAME.lower()]
        newcount = len(newbsp.entities.data)

        ###---------------------------------------------------------------------
        ### DONE --> POST OP
        ###---------------------------------------------------------------------
        ## prepare report:
        ## - summary table
        ## - details
        try:
            report = {
                "summary": (
                    ("Action", "Target", "Changed"),
                    (
                        ("embeds", len(things_to_embed), len(list_embedded)),
                        ("unembeds", len(things_to_unembed), len(list_unembedded)),
                        ("renames", len(remap_dict), len(dict_renamed)),
                        ("remap_entity", info_texture_remap_action.name, newcount - oldcount)
                    )
                ),
                "details": {
                    "embeds": list_embedded,
                    "unembeds": list_unembedded,
                    "renames": dict_renamed
                }
            }
            log.info("BSP Edit summary")
            log.info("=====================================")
            log.info("| Action       | Target   | Changed |")
            log.info("|--------------|----------|---------|")
            log.info("| embeds       | %8d | %7d |", len(things_to_embed), 
                                                     len(list_embedded))
            log.info("| unembeds     | %8d | %7d |", len(things_to_unembed), 
                                                     len(list_unembedded))
            log.info("| renames      | %8d | %7d |", len(remap_dict), 
                                                     len(dict_renamed))
            log.info("| remap entity | %8s | %7d |", info_texture_remap_action.name, 
                                                     newcount - oldcount)
            log.info("'--------------'----------'---------'")
            if show_summary and self.show_summary:
                self.app.view.show_edit_summary(
                    {"input":self.bsppath},
                    report["summary"],
                    report["details"]
                )
        except:
            report = {"summary":(("Error"),(("ERROR"))),"details":{}}

        # return bsp and report in a named tuple
        _r = namedtuple("BspEditResult", ["bsp","report"])
        return _r(newbsp, report) if include_report else _r(newbsp, None)

        ###------------------ END of commit_bsp_edits --------------------------
    
    ###============================= END AppModel ==============================


PropertyBinding = namedtuple("PropertyBinding",["obj","prop"])

@dataclass(frozen=True)
class BindingEntry:
    type : BindingType
    prop : PropertyBinding = None
    data : any = None
    update_predicate  : callable = None
    reflect_predicate : callable = None


@dataclass
class AppView:
    # the parent app
    app : any
    # window binds (the window tag and the view menu item tag)
    window_binds : dict          = field(default_factory=dict)
    # dict of bound items
    bound_items : dict           = field(default_factory=dict)
    # global shared texture registry for all loaded bsp/wad textures
    dpg_texture_registry : int   = field(default_factory=dpg.add_texture_registry)

    # primary struct to hold the name, path, and entry list info
    # and to present the items in the texture pane's wadlist
    wadstats: list[WadStatus]    = field(default_factory=list)
    # holds the miptexes on disk in case user wants to embed them later
    wad_cache : PickledDict      = None # set up in post-init
    # all textures in the bsp
    textures : list[TextureView] = field(default_factory=list)
    # gallery view (only store the filtered items in its data)
    gallery : GalleryView        = field(default_factory=GalleryView)

    # check against issuing dpg commands when viewport isn't ready
    # NOTE: this has been changed to a read-only property method that returns
    # false false if frame count is <4. The existence if _viewport_ready is kept
    # for legacy reasons (cleanup later?)
    #_viewport_ready : bool       = False

    # material entry filter settings
    filter_matchars : str        = ""
    filter_matnames : str        = ""

    # texture remap list settings
    texremap_sort      : bool    = False
    texremap_revsort   : bool    = False
    texremap_grouped   : bool    = False
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
    _gallery_view_props = ( # use to watch updated values and fire gallery render
        "gallery_show_val",
        "gallery_size_val",
        "gallery_size_scale",
        "gallery_size_maxlen",
        "gallery_sort_val",
        "filter_str",
        "filter_unassigned",
        "filter_radiosity"
    )


    def __post_init__(self):
        self.wad_cache = PickledDict(_cache_path=self.app.cfg["basepath"].parent/"temp")
        

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
        if tag not in self.bound_items:
            self.bound_items[tag] = []
        self.bound_items[tag].append(BindingEntry(type, prop, data))
        if type in mappings.writeable_binding_types:
            dpg.configure_item(tag, callback=self.update)


    def update(self,sender,app_data,*_):
        ''' called by the gui item when it updates a prop linked to the model
            prop is a tuple of obj and propname.
            - set value using setattr(*prop, value)
        '''
        if sender not in self.bound_items: return
        for item in self.bound_items[sender]:
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

        for tag,items in self.bound_items.items():
            for item in items:
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
        for k,list in self.bound_items.items():
            for v in list:
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

    @property
    def _viewport_ready(self):
        return dpg.get_frame_count() > 3

    def set_viewport_ready(self,*_):
        if not dpg.get_frame_count():
            # so apparently this fn will _only_ run if frame is 1
            dpg.set_frame_callback(1,callback=lambda:self.set_viewport_ready())
            return
        self.reflect()
        if len(self.textures):
            self.update_gallery()


    def load_textures(self, miptexes, update=False, new_source=None, precedence=999):
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
                    update_args.append((oldtex,newtex,new_source, precedence))

            if not len(update_args): return
            log.info(f"{len(update_args)} texture entries will be updated with {new_source}")
            # transpose list i.e. list 1 is all the texview, #2 is all the miptex, etc.
            argsT = [[row[i] for row in update_args] for i in range(len(update_args[0]))]
            log.debug(f"START UPDATE TEXTURES ({len(argsT[0])})")
            taskfn = failure_returns_none(TextureView.static_update)
            with time_it():
                with ThreadPoolExecutor() as executor:
                    for result in executor.map(taskfn,*argsT):
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

        log.debug(f"load_texture: done.")
        self.update_gallery()
        return result


    def load_external_wad_textures(self, entries:dict[int,Path]):
        ''' loads the textures from the wads, *in order*, then update textures list.
            the input is a dict of entries
            - key being order of precedence
            - value being the path
        '''
        wanted_list = [x.name for x in self.app.data.bsp.textures_x]
        log.info(f"{len(wanted_list)} external textures wanted")
        if not len(wanted_list): return

        wadpaths = entries.values()

        log.info(f"loading all wad files simultaneously-ish...")
        _resultparts = namedtuple("ResultParts", ["miptexes","names"])
        taskfn = failure_returns_none(get_textures_from_wad)
        results = {}
        log.debug("START")
        with time_it():
            with ThreadPoolExecutor() as executor:
                for wadpath, result \
                in zip(wadpaths, executor.map(taskfn, wadpaths,
                                              [wanted_list]*len(wadpaths))):

                    # result is a tuple of loaded miptex list and name list
                    results[wadpath] = _resultparts(*result)

        for order, wadpath in entries.items():
            wadname = Path(wadpath).name
            status = {"loaded": False if results[wadpath] is None else True}

            if results[wadpath].miptexes is None:
                log.warning(f"failed to load textures from {wadname}")

            elif len(results[wadpath].miptexes):
                # something is loaded (empty means can load but found nothing)
                log.debug(f"updating textures with {wadname} ({len(results[wadpath])} items)")

                # fix the miptex name to the waddirentry's.
                # I'm not sure if the engine only considers the waddirentry's name
                # but it makes sense
                # NOTE: result is a dict. translate to list
                miptexes = []
                for direntryname, miptex in results[wadpath].miptexes.items():
                    miptex.name = direntryname
                    miptexes.append(miptex)

                status["loaded_count"] = self.load_textures(miptexes, True, wadname, order)

            else:
                status["loaded_count"] = 0

            # cache the miptexes
            if results[wadpath].miptexes:
                self.wad_cache[wadname] = results[wadpath].miptexes

            log.debug(f"updating wadstats for {wadname}")
            item = next(filter(lambda x:x.name==wadname,self.wadstats),None)
            if item: item.update(**status)


    def update_wadlist(self):
        WadStatus._parent = self.get_dpg_item(type=BindingType.WadListGroup)
        wads = list_wads(self.app.data.bsp.entities,True)

        list(x.delete() for x in self.wadstats) # make sure the bound dpg item is deleted
        self.wadstats = [WadStatus(w,i) for i,w in enumerate(wads)]

        wad_found_paths = search_wads(self.app.data.bsppath, wads)
        for item in self.wadstats:
            item.update(found=bool(wad_found_paths[item.name]))
            item.path = wad_found_paths[item.name]

        self.reflect() #prop=_propbind(self, "wadstats"))


    def update_gallery(self, size_only=False):
        ''' filters the textures list, then passes it off to gallery to render '''
        # all the filters in modelcontroller assembled
        f_a = mappings.gallery_show_map[self.gallery_show_val].filter_fn
        f_u = lambda item: item.matname not in self.app.data.mat_set \
                           and item.matname not in self.app.data.wannabe_set
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
        if not self._viewport_ready: return
        self.gallery.render()
        self.reflect(prop=(self.app,"view"))

    def update_gallery_items(self,matname=None,selected=None):
        ''' update the state of TextureView items '''
        #with dpg.mutex():
        for item in (item for item in self.textures):
            if selected and not item.selected: continue
            elif matname and item.matname != matname: continue
            item.update_state()


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
        table_entry_width = 1 if not len(mat_set) else ceil(log10(len(mat_set)))
        ra = lambda num: str(num).rjust(table_entry_width)

        ### SUMMARY TABLE
        if summary:
            header = (("",0.4), ("Material",1.8), "Count", "Usable", "Assigned")
            data = []
            for mat in mat_set.MATCHARS:
                data.append([ ( ME(mat).value, {"color": mat_color(mat)} ),
                                ME(mat).name,
                                ra(len(mat_set[mat])),
                              ( ra(len(choice_set[mat])),
                                {"color" : avail_colors(len(choice_set[mat]))} ),
                                ra(len(wannabe_set[mat])) ])
            # totals row
            data.append(["", "TOTAL",
                        ra(len(mat_set)), ra(len(choice_set)), ra(len(wannabe_set))])

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
        mat_set = self.app.data.mat_set
        
        ### SUMMARY TABLE ------------------------------------------------------
        table_entry_width = 1 if not len(mat_set) else ceil(log10(len(mat_set)))
        ra = lambda num: str(num).rjust(table_entry_width)
        table = self.get_dpg_item(type=BindingType.MaterialSummaryTable)

        for i, mat in enumerate(self.app.data.wannabe_set.MATCHARS):
            table_cell = gui_utils.traverse_children(table, f"{i}.4")
            dpg.set_value(table_cell, ra(len(self.app.data.wannabe_set[mat])))

        totals_row = len(self.app.data.wannabe_set.MATCHARS)
        table_cell = gui_utils.traverse_children(table, f"{totals_row}.4")
        dpg.set_value(table_cell, ra(len(self.app.data.wannabe_set)))

        ### RENDERING THE TEXTURE REMAP LIST -----------------------------------
        ME = MaterialEnum
        _E = gui_utils.ImglistEntry
        dict_of_lists = {}
        target_len = 48

        def _del_cb(xmat,xmatname):
            def _called(*_):
                self.app.data.wannabe_set[xmat].discard(xmatname.upper())
                self.update_gallery_items(xmatname)
                self.update_wannabe_material_tables()
            return _called

        stages = []
        for mat in self.app.data.wannabe_set.MATCHARS:
            sublist = []

            for matname in self.app.data.wannabe_set[mat]:

                textures = [x for x in self.textures if x.matname==matname]
                with dpg.stage() as content_stage:
                    with dpg.group(horizontal=True):
                        if not self.texremap_grouped:
                            dpg.add_text(f"{matname} {'-'*(15-len(matname))}>")
                            dpg.add_text(mat,color=MaterialColors[mat].color\
                                                   or MaterialColors.unknown.color)
                        else:
                            dpg.add_text(matname)

                    with dpg.group(horizontal=True):
                        dpg.add_text(f"{len(textures)} items")
                        dpg.add_button(label="Del.",
                                       callback=_del_cb(mat,matname))

                if len(textures):
                    sample = textures[0]
                    entry = _E(sample.uuid,sample.width,sample.height,
                               [], matname, content_stage)
                else:
                    entry = _E(None,target_len,target_len,
                               [], matname, content_stage)

                sublist.append(entry)
                stages.append(content_stage)

            dict_of_lists[ME(mat).name] = sublist

        if not self.texremap_grouped:
            dict_of_lists = {"All":list(chain(*dict_of_lists.values()))}

        if self.texremap_sort:
            for sublist in dict_of_lists.values():
                sublist.sort(key=lambda x:x.key, reverse=self.texremap_revsort)

        remap_list = self.get_dpg_item(type=BindingType.TextureRemapList)
        dpg.delete_item(remap_list, children_only=True)

        with dpg.mutex():
            with dpg.stage() as staging:
                for label, imglist in dict_of_lists.items():
                    if self.texremap_not_empty and not len(imglist): continue # hide empty

                    with dpg.tree_node(label=f"{label:8s} ({len(imglist)} entries)",
                                       default_open=True) as node:
                        gui_utils.populate_imglist(node,imglist,target_len)

                    dpg.add_separator()

            dpg.push_container_stack(remap_list)
            dpg.unstage(staging)
            dpg.pop_container_stack()
            dpg.delete_item(staging)

            for temp_item in stages: dpg.delete_item(temp_item)


    def update_window_state(self,sender,app_data):
        ''' synchronize the view menu item's checkbox state
            with the window visibility
        '''
        for tagmap in self.window_binds.values():
            if sender == tagmap["menu"]:
                dpg.configure_item(tagmap["window"], show=app_data)
            else:
                dpg.set_value(tagmap["menu"], dpg.is_item_shown(tagmap["window"]))


    def show_edit_summary(self, base, summary, details):
        ''' base = dict of label-value pairs to show up front
            summary = table struct
            details = dict of node-data view
        '''
        with dpg.mutex():
            id_base = self.get_dpg_item(BindingType.SummaryBase)
            dpg.delete_item(id_base, children_only=True)
            for label, value in base.items():
                dpg.add_input_text(parent=id_base,label=label,
                                   default_value=value,readonly=True)
                with dpg.tooltip(dpg.last_item(),delay=0):
                    dpg.add_text(value)

            id_table = self.get_dpg_item(BindingType.SummaryTable)
            gui_utils.populate_table(id_table,*summary)

            id_details = self.get_dpg_item(BindingType.SummaryDetails)
            dpg.delete_item(id_details, children_only=True)
            for label, data in details.items():
                with dpg.tree_node(label=label,parent=id_details):
                    if isinstance(data,list):
                        dpg.add_text("\n".join(data))
                    elif isinstance(data,dict):
                        dpg.add_text("\n".join([f"{x:15s} : {y}" \
                                                for x,y in data.items()]))

        dpg.show_item(self.get_dpg_item(BindingType.SummaryDialog))


###=============================================================================
###                                   AppActions
###=============================================================================
class AppActions:
    def __init__(self,app,view):
        self.app = app
        self.view = view

        self._init_global_handlers()

    ### GUI callbacks that opens a file dialog ###
    def show_file_dialog(self, type:BindingType, 
                         init_path:str=None, init_filename:str=None, 
                         bound_prop:PropertyBinding=None):
        ''' shows a file dialog bound to the given binding type
            if init_path/filename is given, sets it
            if bound_prop is given, sets the above to the initial value
               and also changes the callback to set the given bound_prop
        '''
        dlg = self.view.get_dpg_item(type)
        
        defaults = {}
        if bound_prop:
            print(bound_prop)
            init_val = Path(getattr(*bound_prop))
            defaults["default_path"]     = init_val.parent
            defaults["default_filename"] = init_val.name
            defaults["callback"] = self._file_dialog_sets_property_callback(bound_prop)
        else:
            if init_path:     defaults["default_path"]     = init_path
            if init_filename: defaults["default_filename"] = init_filename

        dpg.configure_item(dlg, **defaults)
        
        dpg.show_item(dlg)

    def _file_dialog_defaults(self, path, name=None, mapfn=None):
        if not path: return {}
        if callable(mapfn): path = mapfn(path)
        if not name and not path.is_dir(): name, path = path.name, path.parent
        return {"init_path": str(path), "init_filename": str(name)}

    def _file_dialog_sets_property_callback(self, prop_binding:PropertyBinding):
        ''' makes the file dialog callback sets the prop
        '''
        def _cb(sender, app_data):
            setattr(*prop_binding, app_data["file_path_name"])
            self.view.reflect(prop=prop_binding)
        return _cb

    ''' File load/save/export ==================================================
        these file dialogs are already set up to call back the same fn with the name

        gui_utils.message_box calls should use gui_utils.wrap_message_box_callback
        to wrap a callback back to itself, with the "confirm" argument filled with
        the result
        ------------------------------------------------------------------------
    '''
    def has_wip(self):
        ''' check whether user has work in progress, via:
            - wannabe set count
            - count of any texture item with become_external set
        '''
        return len(self.app.data.wannabe_set) \
        or next((x for x in self.app.view.textures if x.become_external is not None),None)
    
    def open_bsp_file(self, bsppath:str|Path=None, confirm=None): # dialog callback
        ''' load bsp, then load wadstats '''
        if self.app.data.bsp and self.has_wip() and confirm is None:
            cb = gui_utils.wrap_message_box_callback(self.open_bsp_file,bsppath)
            gui_utils.confirm(consts.GUI_APPNAME, 
                              "Are you sure you want to open a new BSP?", cb)
            return
        
        elif not bsppath:
            self.show_file_dialog(BindingType.BspOpenFileDialog) # callbacks already set
            return
            
        self.app.data.load_bsp(bsppath)

    def reload(self, *_): # menu callback
        if self.app.data.bsppath:
            self.app.data.load_bsp(self.app.data.bsppath) # kickstarts a lot of loading
            
    def save_bsp_file(self, backup:bool=None, confirm=None):
        ## checking it ---------------------------------------------------------
        if not self.app.data.bsppath: return # nothing to save

        bakpath = self.app.data.bsppath.with_name(self.app.data.bsppath.name + ".bak")
        should_backup = not bakpath.exists()

        if confirm == 0: return
        elif confirm == 1: backup=True
        elif should_backup and not backup and confirm is None:
            cb_wrap = gui_utils.wrap_message_box_callback(self.save_bsp_file,backup)
            gui_utils.message_box(
                    "Confirm overwrite",
                    f'Are you sure you want to overwrite "{self.app.data.bsppath.name}" without backup?', cb_wrap,
                    {1:"Backup and save",2:"Save WITHOUT backup",0:"Cancel"})
            return

        ## doing it ------------------------------------------------------------
        if backup:
            backup_file(self.app.data.bsppath)

        result = self.app.data.commit_bsp_edits()
        with open(self.app.data.bsppath, "wb") as f:
            result.bsp.dump(f)

        log.info('Saved BSP file: "%s"', self.app.data.bsppath)


    def save_bsp_file_as(self, bsppath:str|Path=None, confirm=None):
        ## checking it ---------------------------------------------------------
        if not self.app.data.bsppath: return # nothing to save
        if not bsppath:
            mapfn = lambda p:p.with_name(p.stem + "_output.bsp")
            kwargs = self._file_dialog_defaults(self.app.data.bsppath,mapfn=mapfn)
            self.show_file_dialog(BindingType.BspSaveFileDialog,**kwargs)
            return

        elif Path(bsppath).exists() and not confirm:
            cb_wrap = gui_utils.wrap_message_box_callback(self.save_bsp_file_as,bsppath)
            gui_utils.confirm_replace(bsppath, cb_wrap)
            return

        ## doing it ------------------------------------------------------------
        result = self.app.data.commit_bsp_edits(include_report=True,show_summary=False)
        with open(bsppath, "wb") as f:
            result.bsp.dump(f)

        log.info('Saved BSP file: "%s"', bsppath)

        if self.app.data.show_summary:
            self.app.view.show_edit_summary(
                {"input":self.app.data.bsppath,"output":bsppath},
                result.report["summary"],
                result.report["details"]
            )


    def load_mat_file(self, matpath:str|Path=None): # dialog callback
        if not matpath:
            self.show_file_dialog(BindingType.MatLoadFileDialog) # callbacks already set
            return
        self.app.data.load_materials(matpath)

    def load_custommat_file(self, matpath:str|Path=None): # dialog callback
        if not matpath:
            mapfn = bsp_custommat_path
            kwargs = self._file_dialog_defaults(self.app.data.bsppath,mapfn=mapfn)
            self.show_file_dialog(BindingType.CustomMatLoadFileDialog,**kwargs)
            return

        self.app.data.load_wannabes(matpath)

    def export_custommat(self, outpath:str|Path=None, confirm=None):
        if confirm==False: return
        elif not len(self.app.data.wannabe_set): return
        if not outpath:
            mapfn = bsp_custommat_path
            kwargs = self._file_dialog_defaults(self.app.data.bsppath,mapfn=mapfn)
            self.show_file_dialog(BindingType.CustomMatExportFileDialog,**kwargs)
            return

        elif Path(outpath).exists() and not confirm:
            cb_wrap = gui_utils.wrap_message_box_callback(self.export_custommat,outpath)
            gui_utils.confirm_replace(str(outpath), cb_wrap)
            return

        try:
            dump_texinfo(self.app.data.bsppath,7168, None, # header|matchars|mat_set
                         material_set=self.app.data.wannabe_set,
                         outpath=Path(outpath),
                         wadlist=[item.name for item in self.view.wadstats if item.loaded])
            log.info(f"Exported custom material file: \"{outpath}\"")
        except Exception as error:
            log.error(f"Failed to export custom material file: \"{outpath}\"\n\t{error}")

    def clear_wannabes(self,confirm=None):
        if confirm==False: return
        elif not len(self.app.data.wannabe_set): return
        elif confirm is None:
            cb_wrap = gui_utils.wrap_message_box_callback(self.clear_wannabes)
            gui_utils.confirm("Clear remap list",
                              f"{len(self.app.data.wannabe_set)} entries will be cleared. continue?", cb_wrap)
            return

        self.app.data.wannabe_set = MaterialSet()
        self.view.update_gallery_items()
        self.view.update_wannabe_material_tables()

    ## parse entity in bsp (just a passthrough)
    def parse_remap_entities(self, *_):
        self.app.data.parse_remap_entities()

    ## wad selection callback
    def load_selected_wads(self, *_): # button callback
        entries = {x.order: x.path for x in self.view.wadstats if x.selected}
        self.app.view.load_external_wad_textures(entries)

    ## Gallery actions =========================================================
    def select_all_textures(self, sender, _, value:bool=False):
        log.debug(f"selection: {value}")
        for item in self.view.gallery.data: # only the list in gallery data is selectable
            # item._select_cb(sender,value)
            item.selected = True
        self.view.update_gallery_items()

    def select_wannabes(self,*_): # select textures in wannabe set
        union = dpg.is_key_down(dpg.mvKey_Control)
        print(self.app.data.wannabe_set)
        for item in self.view.gallery.data:
            if item.matname in self.app.data.wannabe_set:
                item.selected = True
            elif not union:
                item.selected = False
        self.view.update_gallery_items()

    def selection_set_material(self, sender, _, mat:str):
        for item in self.view.gallery.data:
            if item.selected:
                item.mat = mat
        self.view.update_gallery_items(selected=True)

    def selection_embed(self, sender, _, embed:bool):
        for item in self.view.gallery.data:
            if item.selected:
                item.become_external = None if embed != item.is_external else not embed
        self.view.update_gallery_items(selected=True)

    def show_config(self, *_):
        dpg.show_item(self.view.get_dpg_item(BindingType.ConfigDialog))

    def show_about(self, *_):
        dpg.show_item(self.view.get_dpg_item(BindingType.AboutDialog))

    def close(self, confirm=None):
        if confirm is None and self.has_wip():
            cb = gui_utils.wrap_message_box_callback(self.close)
            gui_utils.confirm("Close BSP", "Are you sure you want to close?", cb)
            return
            
        self.app.reset()

    def quit(self, confirm=None):
        if confirm is None and self.has_wip():
            cb = gui_utils.wrap_message_box_callback(self.quit)
            gui_utils.confirm(f"Exit {consts.GUI_APPNAME}", 
                              "Are you sure you want to exit?", cb)
            return
        
        dpg.stop_dearpygui() # stop the render loop
        

    ## handles dropped txt files
    def open_text_file_as(self, filepath, type=None):
        if type==1 or Path(filepath).name.lower() == "materials.txt":
            self.app.data.load_materials(Path(filepath))
        elif type==2:
            self.app.data.load_wannabes(Path(filepath))
        elif type is None:
            cb = gui_utils.wrap_message_box_callback(self.open_text_file_as, filepath,
                                                     _result_arg="type")
            btns = {1: "Reference materials.txt",
                    2: "Custom material remap file",
                    0: "Cancel"}
            gui_utils.message_box("Open file as", f'"{Path(filepath).name}" is a:',
                                  cb, btns, gui_utils.MsgBoxOptions.VerticalButtons)
            return

    ## file drop
    def handle_drop(self, data, keys): # DearPyGui_DragAndDrop
        if not isinstance(data, list): return
        suffix = Path(data[0]).suffix.lower()
        if suffix == ".bsp":
            self.app.data.load_bsp(data[0])
        elif suffix == ".txt":
            self.open_text_file_as(Path(data[0]))
        elif suffix == ".wad":
            # TEST
            self.app.data.TEST_load_wad(data[0])


    ### GLOBAL IO handlers ###
    def _init_global_handlers(self):
        with dpg.handler_registry() as global_handler:
            dpg.add_mouse_down_handler(callback=self.on_mouse_down)
            dpg.add_mouse_release_handler(callback=self.on_mouse_up)
            dpg.add_mouse_click_handler(dpg.mvMouseButton_Left,
                                        callback=self.on_mouse_click)
            dpg.add_mouse_click_handler(dpg.mvMouseButton_Right,
                                        callback=self.on_mouse_rclick)
            dpg.add_mouse_click_handler(dpg.mvMouseButton_Middle,
                                        callback=self.on_mouse_mclick)
            dpg.add_mouse_double_click_handler(callback=self.on_mouse_dblclick)
            dpg.add_mouse_wheel_handler(callback=self.on_mouse_wheel)
            dpg.add_mouse_move_handler(callback=self.on_mouse_move)
            dpg.add_mouse_drag_handler(callback=self.on_mouse_drag)

    def on_mouse_x(self,cbname,sender,data):
        try: self._mouse_callbacks[cbname](data)
        except (AttributeError, KeyError, TypeError): pass

    def on_mouse_down (self,sender,data):  self.on_mouse_x("mouse_down", sender,data)
    def on_mouse_up   (self,sender,data):  self.on_mouse_x("mouse_up",   sender,data)
    def on_mouse_click(self,sender,data):  self.on_mouse_x("mouse_click",sender,data)
    def on_mouse_rclick(self,sender,data): self.on_mouse_x("mouse_rclick",sender,data)
    def on_mouse_mclick(self,sender,data): self.on_mouse_x("mouse_mclick",sender,data)
    def on_mouse_dblclick(self,sender,data): self.on_mouse_x("mouse_dblclick",sender,data)
    def on_mouse_wheel(self,sender,data):  self.on_mouse_x("mouse_wheel",sender,data)
    def on_mouse_move (self,sender,data):  self.on_mouse_x("mouse_move", sender,data)
    def on_mouse_drag (self,sender,data):  self.on_mouse_x("mouse_drag", sender,data)

    def set_mouse_event_target(self,sender=None,callbacks=None):
        ''' on hover, call this to send the mouse event over to the callbacks
            since this is a continuous process, we set a frame callback on the
            next frame to clear everything
        '''
        self._mouse_event_target = sender
        self._mouse_callbacks = callbacks
        ## clear on next frame
        dpg.set_frame_callback(dpg.get_frame_count()+2,
                               lambda: self.set_mouse_event_target())


class AppCfg(dict):
    ''' makes app.cfg accessible to getattr(*prop) '''
    def __getattr__(self, attr:str) -> str:
        return super().get(attr)
    def __setattr__(self, attr:str, val:str) -> None:
        super().update({attr: val})

class App:
    def __init__(self, basepath=None):
        if not basepath:
            basepath = Path(sys.modules['__main__'].__file__)
        
        # setup config first, as MVC might depend on its values
        self.cfg = AppCfg({
            "basepath": basepath,
            "cfgpath": basepath.with_name("BspTexRemap.cfg.toml"),
            "usercfgpath": basepath.with_suffix(".cfg.json"),
            "use_multithread" : True, # unused
            
            "bsp_viewer" : ""
        })
        self.load_config()

        self.data = AppModel(self)
        self.view = AppView(self) # reads cfg.basepath for wad_cache
        self.do = AppActions(self,self.view)

        TextureView.class_init(app=self,
                               mat_update_cb=self.view.update_wannabe_material_tables,
                               mouse_event_registrar=self.do.set_mouse_event_target,
                               #global_texture_registry=self.global_texture_registry)
                               global_texture_registry=self.view.dpg_texture_registry)


    ## loading and saving config
    def load_config(self):
        # load the TOML file
        cfgpath = self.cfg["cfgpath"]
        self.cfg.update(tomllib.loads(Path(cfgpath).read_text()))
        
        # load the user config json
        usercfgpath = self.cfg["usercfgpath"]

        try:
            cfg = json.loads(Path(usercfgpath).read_bytes())
            if cfg["appname"] != consts.GUI_APPNAME: return
        except: return

        for part, prop in mappings.CONFIG_MAP:
            try: setattr(getattr(self, part),prop, cfg["config"][part][prop])
            except: continue

    def save_config(self):
        usercfgpath = self.cfg["usercfgpath"]

        cfg = {"appname" : consts.GUI_APPNAME, "config": {} }
        for part, prop in mappings.CONFIG_MAP:
            cfg["config"].setdefault(part,{})[prop] = getattr(getattr(self, part), prop)

        try: Path(usercfgpath).write_text(json.dumps(cfg))
        except: log.warning("Couldn't write layout config file")

    def reset(self, reflect=True):
        self.data.bsppath      = None
        self.data.bsp          = None
        self.data.matpath      = None
        self.data.mat_set      = MaterialSet()
        self.data.wannabe_set  = MaterialSet()
        self.data.direct_remap = dict()
        
        list(x.delete() for x in self.view.wadstats)
        self.view.wadstats = []
        self.view.textures = []
        dpg.delete_item(self.view.dpg_texture_registry, children_only=True)
        
        if reflect:
            self.view.reflect()
            self.view.update_gallery()
            self.view.render_material_tables()
            self.view.update_wannabe_material_tables()
            
        log.info("App reset.")

