from enum import IntEnum, IntFlag, auto
from collections import namedtuple

## CONFIG MAP
CONFIG_MAP = (
    ("data", "auto_load_materials"),
    ("data", "auto_load_wads"     ),
    ("data", "auto_load_wannabes" ),
    ("data", "allow_unembed"      ),
    ("data", "remap_entity_action"),
    ("data", "backup"             ),
    ("data", "show_summary"       ),
    ("view", "texremap_sort"      ),
    ("view", "texremap_revsort"   ),
    ("view", "texremap_grouped"   ),
    ("view", "texremap_not_empty" ),
#    ("view", "gallery_show_val"   ),
    ("view", "gallery_size_val"   ),
    ("view", "gallery_size_scale" ),
    ("view", "gallery_size_maxlen"),
    ("view", "gallery_sort_val"   ),
    ("view", "filter_unassigned"  ),
    ("view", "filter_radiosity"   )
)

class BindingType(IntEnum):
                                       # Readonly
                                       #    data desc
    Value                     = auto() #    -
    ValueIs                   = auto() #    associated val. gets/sets bool
    TextMappedValue           = auto() #    prop in mappings
    FormatLabel               = auto() # R  [fmtstr, prop map]
    FormatValue               = auto() # R  [fmtstr, prop map]
    #FilterValue               = auto()
    #FilterSet                 = auto()

    # the following are enums for targetting particular items
    TexturesWindow            = auto()
    MaterialsWindow           = auto()
    RemapsWindow              = auto()
    OptionsWindow             = auto()
    LogWindow                 = auto()

    BspOpenFileDialog         = auto()
    BspSaveFileDialog         = auto()
    MatLoadFileDialog         = auto()
    CustomMatLoadFileDialog   = auto()
    CustomMatExportFileDialog = auto()
    MaterialSummaryTable      = auto()
    MaterialEntriesTable      = auto()
    TextureRemapList          = auto()
    WadListGroup              = auto()
    GallerySizeList           = auto()
    GalleryRoot               = auto()

    SummaryDialog             = auto()
    SummaryBase               = auto()
    SummaryTable              = auto()
    SummaryDetails            = auto()


read_only_binding_types = (BindingType.FormatLabel,
                           BindingType.FormatValue)
writeable_binding_types = (BindingType.Value,
                           BindingType.ValueIs,
                           BindingType.TextMappedValue)
reflect_all_binding_types = read_only_binding_types + writeable_binding_types

_galshow = namedtuple("GalleryViewEntry", ["text", "short", "filter_fn"])
gallery_show_map = [
    _galshow("Embedded","M", lambda item:not item.is_external),
    _galshow("External","X", lambda item:item.is_external),
    _galshow("All"     ,"A", lambda item:True)
]
gallery_show = [item.text for item in gallery_show_map]


_galsize = namedtuple("GallerySizeEntry", ["text", "scale", "max_length"])
gallery_size_map = [
    _galsize("Double size (200%)",  2.0, float('inf')),
    _galsize("Full size (100%)",    1.0, float('inf')),
    _galsize("Half size (50%)",     0.5, float('inf')),
    _galsize("256px max. length",   1.0, 256),
    _galsize("128px max. length",   1.0, 128),
    # use the sliders. must be last item!
    _galsize("Custom",              1.0, float('inf')),
]
gallery_sizes = [item.text for item in gallery_size_map]

_galsort = namedtuple("GallerySortEntry", ["text", "short", "key", "reverse"])
gallery_sort_map = [
    _galsort("By entry order (no sort)",     "--", lambda x:0,         False),
    _galsort("By texture name, ascending" ,  "+N", lambda x:x.name,    False),
    _galsort("By texture name, descending",  "-N", lambda x:x.name,    True ),
    _galsort("By material name, ascending" , "+M", lambda x:x.matname, False),
    _galsort("By material name, descending", "-M", lambda x:x.matname, True ),
    _galsort("By width, ascending" ,         "+W", lambda x:x.width,   False),
    _galsort("By width, descending",         "-W", lambda x:x.width,   True ),
    _galsort("By height, ascending" ,        "+H", lambda x:x.height,  False),
    _galsort("By height, descending",        "-H", lambda x:x.height,  True ),
    _galsort("By dimensions, ascending" ,    "+S", lambda x:x.width*x.height, False),
    _galsort("By dimensions, descending",    "-S", lambda x:x.width*x.height, True ),
]
gallery_sortings = [item.text for item in gallery_sort_map]
gallery_sort_separators = (5,) # where separators at


class RemapEntityActions(IntEnum):
    Insert   = auto()
    Remove   = auto()
    NoAction = auto()

_act = namedtuple("ActionMap", ["text", "value"])
remap_entity_actions_map = [
    _act("Insert texture remappings", RemapEntityActions.Insert  ),
    _act("Remove entity",             RemapEntityActions.Remove  ),
    _act("No action",                 RemapEntityActions.NoAction)
]
remap_entity_actions = [item.text for item in remap_entity_actions_map]

