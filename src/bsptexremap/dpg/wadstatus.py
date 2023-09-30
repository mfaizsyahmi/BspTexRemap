''' wadstatus.py
    holds the wadstatus class, which encapsulates data about wad paths in the bsp
    as well as presenting them in the gui
'''
import dearpygui.dearpygui as dpg
from pathlib import Path
from dataclasses import dataclass, field #, asdict
from collections import UserList
from typing import ClassVar
import re, logging

log = logging.getLogger(__name__)


@dataclass
class WadStatus:
    ''' the primary data class to hold wad information 
        todo: remove all the other vars that hold wad information
    '''

    # data
    name    : str
    order   : int  = 0 # of precedence, a way to prioritise loading textures
    path    : Path = None
    entries : list[str] = None # load_external_wad_textures returns this
    
    # view status
    found : bool = None  # true=yes, false=no,         none=no action
    loaded : bool = None # true=yes, false=can't load, none=no action
    selected : bool = False
    uuid : any = None
    loaded_count : int = 0
    
    # consts
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

    def update(self, found=None, loaded=None, loaded_count=None,
               entries = None):
        if found is not None: self.found = found
        if loaded: self.loaded = loaded
        if loaded_count: self.loaded_count = loaded_count
        if entries: self.entries = entries
        
        dpg.configure_item(self.uuid,
                           label=self._fmt(),
                           enabled=False if self.found is False else True)


class WadList(UserList):
    ''' extends list by letting you use wad name as key 
        (the lsit should already be contiguously ordered)
    '''
    def __getitem__(self, key):
        if isinstance(key,str):
            return next((x for x in self.data if x.name == key),None)
        else:
            return self.data[key]

