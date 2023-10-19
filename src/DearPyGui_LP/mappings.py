''' map.py
    Copyright (c) 2023 M Faiz Syahmi @ kimilil
    Released under MIT License
    
    Contains the mapping dict between markup element name and dpg constructor for DPG_LP.
'''
import dearpygui.dearpygui as dpg
from . import buildfuncs as bfn
from collections import namedtuple

DpgNodeMap = namedtuple("DpgNodeMap",["fn","kwargs", "child_content_slice"],defaults=[None])
_m = DpgNodeMap # shorthand
DPG_NODE_KW_MAP = {
    "GROUP"   : _m(dpg.add_group, {}),
    "HGROUP"  : _m(dpg.add_group, {"horizontal":True}),
    
    "HR"      : _m(dpg.add_separator, {}),
    
    "HEADER"  : _m(dpg.add_collapsing_header, {}),
    "+HEADER" : _m(dpg.add_collapsing_header, {"default_open":False}),
    "-HEADER" : _m(dpg.add_collapsing_header, {"default_open":True}),
    "=HEADER" : _m(dpg.add_collapsing_header, {"leaf":True}),
    
    "NODE"    : _m(dpg.add_tree_node, {}),
    "+NODE"   : _m(dpg.add_tree_node, {"default_open":False}),
    "-NODE"   : _m(dpg.add_tree_node, {"default_open":True}),
    "=NODE"   : _m(dpg.add_tree_node, {"leaf":True}),
    
    "TABLE"   : _m(dpg.add_table, {}),
    "TBLCOL"  : _m(dpg.add_table_column, {}),
    "TBLROW"  : _m(dpg.add_table_row, {}),
    "COL"     : _m(dpg.add_table_column, {}),
    "ROW"     : _m(dpg.add_table_row, {}),
    
    ## the following are not containers. its children is its value.
    ## the third DpgNodeMap entry specifies the slice of the children to become the value
    ## in most cases it'd be slice(1) but for listbox & co it's slice(really_big_number)
    "IMG"     : _m(bfn.add_image, {}, slice(1)),
    
    "TEXT"    : _m(dpg.add_text, {"wrap":0}, slice(1)),
    "-TEXT"   : _m(dpg.add_text, {"wrap":0, "bullet":True}, slice(1)),
    "URL"     : _m(bfn.add_url_text, {"wrap":0, "color":(100,100,240)}, slice(1)),
    "LISTBOX" : _m(dpg.add_listbox, {}, slice(0x7FFFFFFF)),
    "COMBOBOX": _m(dpg.add_combo, {}, slice(0x7FFFFFFF)),
    "COMBO"   : _m(dpg.add_combo, {}, slice(0x7FFFFFFF)),
    "RADIO"   : _m(dpg.add_radio_button, {}, slice(0x7FFFFFFF)),
    "HRADIO"  : _m(dpg.add_radio_button, {"horizontal":True}, slice(0x7FFFFFFF)),
}
BINDINGS = {
    "bind"  : dpg.bind_item_handler_registry,
    "theme" : dpg.bind_item_theme,
    "font"  : dpg.bind_item_font,
}

# add callback functions to this. during tree parsing, swap defined value in kwargs
# with the mapped callback fn
CALLBACKS = {}
