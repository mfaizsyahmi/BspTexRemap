''' consts.py
    all constants go here

    to use it in other files:
    >>> from . import consts
    >>> consts.CHARSEQUENCE
'''
from ..consts import *
from pathlib import Path
import sys

### ABOUT ======================================================================
GUI_APPNAME     = "BspTexRemap GUI"
GUI_VERSION     = "v0.1"
GUI_APPDESC     = """
View textures in GoldSrc BSP files, loads materials.txt, assigns custom materials to the textures in the BSP, renames those textures in a way that applies material sounds without modifying materials.txt.
""".strip()

GUI_ABOUT = f"""
{GUI_APPNAME} {GUI_VERSION}
{COPYRIGHT}

{GUI_APPDESC}

Part of {APPNAME} {VERSION}
Released under MIT License
({PROJECT_URL})

Written in Python 3.11.5
Uses DearPyGui v1.10.0 by hoffstadt under MIT License (https://github.com/hoffstadt/DearPyGui)
Uses DearPyGui-DragAndDrop by IvanNazaruk under MIT License (https://github.com/IvanNazaruk/DearPyGui-DragAndDrop)
""".strip()

### main file ==================================================================
AUTOLOAD_REMAPS_HELP = """ 
Loads existing texture remap entries from the following sources:
  1. info_texture_remap entities in map
  2. <mapname>_custommat.txt file
""".strip()

GALLERY_STATUS_LEGEND = """
M - embedded textures
X - external textures
T - total textures
V - textures in view
S - textures selected
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

NOTES = """
NOTES:
0) Load WADs: Texture window > Show > Select WADs > Load Selected
1) You can only rename embedded textures. To rename WAD textures, load the WAD first, then embed them.
2) Focus on textures for surfaces that can be walked on, as step sounds have tactical value. (MDVGTS)
3) The exported _custommat.txt is useful as a "save" format. Export often.
""".strip()

# texview.py
TEXVIEW_MX = ("Embedded", "External")
