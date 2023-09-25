from enum import IntEnum, IntFlag, auto
from collections import namedtuple

class BindingType(IntEnum):
                                    # Unique
                                    #   Readonly
                                    #      data desc
    Value                = auto()   #      -
    ValueIs              = auto()   #      associated val. gets/sets bool
    TextMappedValue      = auto()   #      prop in mappings
    FormatLabel          = auto()   #   R  [fmtstr, prop map]
    FormatValue          = auto()   #   R  [fmtstr, prop map]
    FilterValue          = auto()   #
    FilterSet            = auto()   #
    BspOpenFileDialog    = auto()   # U
    BspSaveFileDialog    = auto()   # U
    MatLoadFileDialog    = auto()   # U
    MatExportFileDialog  = auto()   # U
    MaterialSummaryTable = auto()   # U
    MaterialEntriesTable = auto()   # U
    TextureRemapList     = auto()   # U
    WadListGroup         = auto()   # U
    GallerySizeList      = auto()   # U
    GalleryRoot          = auto()   # U

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
