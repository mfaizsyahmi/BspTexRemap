from enum import IntFlag, auto

class BindingFlag(IntFlag):
    ReadOnly    = auto()
    Flag        = auto()
    ListValues  = auto() # combo/listbox/radiobutton
_bf = BindingFlag # shorthand

# map of target tags
target = {
    "dlgBspFileOpen"    :"dlgBspFileOpen",
    "dlgBspFileSaveAs"  :"dlgBspFileSaveAs",
    "dlgMatFileOpen"    :"dlgMatFileOpen",
    "dlgMatFileExport"  :"dlgMatFileExport",
    "tblMatSummary"     :"tblMatSummary",
    "tblMatEntries"     :"tblMatEntries",
    "grpWadlist"        :"grpWadlist", # populate wad list as selectable
    "cboGallerySize"    :"cboGallerySize", # gallery size combobox
}

gallery_show_filters = {
    "Embedded": lambda item:not item.is_external,
    "External": lambda item:item.is_external,
    "All": lambda item:True
}
gallery_show = list(gallery_show_filters.keys())

gallery_size_map = [
    ("Double size (200%)", 2.0, None),
    ("Full size (100%)",   1.0, None),
    ("256px max. width",   1.0, 256 ),
    ("128px max. width",   1.0, 128 )
]
gallery_sizes = [item[0] for item in gallery_size_map]

bindings = [
    # [0]: dpg input type
    # [2]: associated value:- list/combo/radio=list, flag value if flag
    # [3]: flag
    # [0]           app prop              [2]            [3]   
    ("input_text", "matpath",             None,          _bf(0) ),
    ("input_text", "filter_matchars",     None,          _bf(0) ),
    ("input_text", "filter_matnames",     None,          _bf(0) ),
    ("checkbox",   "auto_load_materials", None,          _bf(0) ),
    ("checkbox",   "auto_load_wads",      None,          _bf(0) ),
    ("checkbox",   "insert_remap_entity", None,          _bf(0) ),
    ("checkbox",   "backup",              None,          _bf(0) ),
    ("combo",      "gallery_size_text",   gallery_sizes, _bf.ListValues)
]
