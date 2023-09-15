''' utils.py
    utility functions go here. that is, functions that has no side effects
    
    to use it in other files:
    >>> from .utils import *
'''
from . import consts
from .enums import MaterialEnum
import re # modpath_fallbacks
from itertools import product # char_padder
from jankbsp import BspFile
from pathlib import Path
import sys, os, logging
log = logging.getLogger(__name__)


def char_padder(len:int) -> str:
    ''' generator of character paddings of given length
    '''
    for result in product(consts.CHARSEQUENCE, repeat=len):
        yield "".join(result)

def bsp_texinfo_path(bsppath):
    return bsppath.with_name(bsppath.stem + consts.TEXINFO_SUFFIX + consts.TEXINFO_FMT)
    
def bsp_custommat_path(bsppath):
    return bsppath.with_name(bsppath.stem + consts.CUSTOMMAT_SUFFIX + consts.CUSTOMMAT_FMT)

def infolog_material_set(material_set):
    if log.getEffectiveLevel() > logging.INFO: return
    
    log.info("x | material |  num")
    log.info("--+----------+-----")
    for m,s in material_set.asdict().items():
        log.info(f"{m} | {MaterialEnum(m).name:8s} | {len(s):>4d}")

def flag_str_parser(flagenum):
    def callfn(values):
        parts = re.split(r"[|+ ]", values)
        parts = [int(val) if val.isdigit() else val for val in parts]
        result = flagenum(0)
        for item in flagenum:
            for val in parts:
                if isinstance(val, int):
                    if val&item.value:
                        result |= item
                elif item.name.lower() == val.lower():
                    result |= item
        log.debug(result)
        return result
    return callfn

