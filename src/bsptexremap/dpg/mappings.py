
# map of target tags
target = {
    "tblMatSummary"     :"tblMatSummary",
    "dlgBspFileOpen"    :"dlgBspFileOpen",
    "dlgBspFileSaveAs"  :"dlgBspFileSaveAs",
    "dlgMatFileOpen"    :"dlgMatFileOpen",
    "dlgMatFileExport"  :"dlgMatFileExport",
}
bindings = [
    # [0]: dpg input type
    # [2]: if not None, &= the prop with this value
    # [3]: read only
    # [0]           app prop              [2]
    ("input_text", "matpath",             None, False),
    ("checkbox",   "auto_load_materials", None, False),
    ("checkbox",   "auto_load_wads",      None, False),
    ("checkbox",   "insert_remap_entity", None, False),
    ("checkbox",   "backup",              None, False),
]
gallery_view_map = [
    ("Double size (200%)", 2.0, None),
    ("Full size (100%)",   1.0, None),
    ("256px max. width",   1.0, 256 ),
    ("128px max. width",   1.0, 128 )
]
