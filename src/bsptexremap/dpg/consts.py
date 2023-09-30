''' consts.py
    all constants go here

    to use it in other files:
    >>> from . import consts
    >>> consts.CHARSEQUENCE
'''
from ..consts import * # base of this file

# these should overwrite the one in the base file
GUI_APPNAME     = "BspTexRemap GUI"
GUI_VERSION     = "v0.1"

# main file
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

# texview.py
TEXVIEW_MX = ("Embedded", "External")