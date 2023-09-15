''' bsputil.py
    BspFile related util functions
'''
from . import consts
from .materials import MaterialSet
from jankbsp import BspFile
from pathlib import Path


def iter_texremap_entities(bsp_entities) -> list:
    fn = lambda ent: ent["classname"] == consts.TEXREMAP_ENTITY_CLASSNAME
    return filter(fn, bsp_entities)

def list_textures(miptexlist):
    return map(lambda t:t.name,miptexlist)

def list_texgroups(miptexlist):
    return set([MaterialSet.strip(t.name.upper()) for t in miptexlist])

def remap_texnames(func, miptexlist):
    for miptex in miptexlist:
        miptex.name = func(miptex.name)

def wadlist(bsp_entities, strip_paths=False) -> list[str]:
    wads = bsp_entities[0]["wad"].split(";")
    wads = [Path(item).name if strip_paths else item for item in wads]
    return wads
