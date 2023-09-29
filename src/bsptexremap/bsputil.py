''' bsputil.py
    BspFile related util functions
    
'''
from . import consts
from .materials import MaterialSet
from jankbsp import BspFile
from jankbsp.enums import Lumps, BlueShiftLumps
from pathlib import Path
import re

##------------------------------
## routines working with bsppath
##------------------------------

def bsp_modname_from_path(bsppath:Path):
    return re.sub(consts.MODNAME_SUFFIX_RE, '', bsppath.parents[1].name)

def bsp_texinfo_path(bsppath:Path) -> Path:
    return bsppath.with_name(bsppath.stem + consts.TEXINFO_SUFFIX + consts.TEXINFO_FMT)
    
def bsp_custommat_path(bsppath:Path) -> Path:
    return bsppath.with_name(bsppath.stem + consts.CUSTOMMAT_SUFFIX + consts.CUSTOMMAT_FMT)

def guess_lumpenum(bsppath:Path):
    ''' if path is in blue shift, return the blue shift enum
        else the regular enum
    '''
    if Path(bsppath).parents[1].name.lower().startswith("bshift"):
        return BlueShiftLumps
    else: return Lumps


##-----------------------------------
## routines working with bsp entities
##-----------------------------------

def iter_texremap_entities(bsp_entities) -> list:
    fn = lambda ent: ent["classname"] == consts.TEXREMAP_ENTITY_CLASSNAME
    return filter(fn, bsp_entities)

def list_wads(bsp_entities, strip_paths=False) -> tuple[str]:
    if "wad" not in bsp_entities[0]: return tuple() # some maps actually don't have these
    wads = bsp_entities[0]["wad"].split(";")
    wads = list(filter(lambda x:len(x),wads)) # removes empty item at the end
    wads = [Path(item).name if strip_paths else item for item in wads]
    return tuple(wads)

def wadlist(*args, **kwargs): return list_wads(*args, **kwargs) # old name alias


##-------------------------------
## routines working with textures
##-------------------------------

def list_textures(miptexlist):
    return map(lambda t:t.name,miptexlist)

def list_texgroups(miptexlist):
    return set([MaterialSet.strip(t.name.upper()) for t in miptexlist])

def remap_texnames(func, miptexlist):
    for miptex in miptexlist:
        miptex.name = func(miptex.name)

