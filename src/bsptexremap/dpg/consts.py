''' consts.py
    all constants go here

    to use it in other files:
    >>> from . import consts
    >>> consts.CHARSEQUENCE
'''
from ..consts import *
# these should overwrite the one in the base file
GUI_APPNAME     = "BspTexRemap GUI"
GUI_VERSION     = "v0.1"

## CONFIG MAP
CONFIG_MAP = (
    ("data", "auto_load_materials"),
    ("data", "auto_load_wads"     ),
    ("data", "auto_load_wannabes" ),
    ("data", "allow_unembed"      ),
    ("data", "remap_entity_action"),
    ("data", "backup"             ),
    ("view", "texremap_sort"      ),
    ("view", "texremap_revsort"   ),
    ("view", "texremap_grouped"   ),
    ("view", "texremap_not_empty" ),
    ("view", "gallery_show_val"   ),
    ("view", "gallery_size_val"   ),
    ("view", "gallery_size_scale" ),
    ("view", "gallery_size_maxlen"),
    ("view", "gallery_sort_val"   )
)

# main file
AUTOLOAD_REMAPS_HELP = """ 
Loads existing texture remap entries from the following sources:
  1. info_texture_remap entities in map
  2. <mapname>_custommat.txt file
""".strip()
        
REMAP_ENTITY_ACTION_HELP = """
info_texture_remap is an entity that mappers can insert to remap entities.
It is primarily used with the command line version BspTexRemap as part of the
post-compilation step.

Options:
- {0}: Inserts this entity, or updates its entries.
  If you forgo this step, the texture renamings would be irreversible.
- {1}: Removes all instances of this entity.
- {2}
""".strip()

ALLOW_UNEMBED_HELP = """
A check against unembedding embedded textures without the corresponding WAD.
It is your responsibility to ensure that the wad list contains a WAD that has
the textures you're unembedding, or you'll have missing textures.
""".strip()

# texview.py
TEXVIEW_MX = ("Embedded", "External")
