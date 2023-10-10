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
from functools import reduce # filterstring_to_filter
import logging
log = logging.getLogger(__name__)


def failure_returns_none(func):
    ''' wraps function so that if it fails, returns none
        this is to be used for executing get_textures_from_wad concurrently
    '''
    def wrap(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
        except:
            result = None
        return result
    return wrap
    
    
def char_padder(len:int) -> str:
    ''' generator of character paddings of given length
    '''
    for result in product(consts.CHARSEQUENCE, repeat=len):
        yield "".join(result)


def infolog_material_set(material_set):
    if log.getEffectiveLevel() > logging.INFO: return
    
    log.info("x | material |  num")
    log.info("--+----------+-----")
    for m,s in material_set.asdict().items():
        log.info(f"{m} | {MaterialEnum(m).name:8s} | {len(s):>4d}")

def flag_str_parser(flagenum):
    ''' returns a callable that parses a string value that resolves to a combined 
        flag value
    '''
    def callfn(values):
        ''' parses given delimited string value against IntFlag values and boils
            it down to a single combined value.
            this is used to parse dump_texinfo value.
            separators can be any of + | " ", but the command prompt/shell 
            normally interprets | as a command pipe.
        '''
        parts = values if isinstance(values, list) else re.split(r"[|+ ]", values)
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

def filterstring_to_filter(filter_str):
    fragments = [x.lower() for x in filter_str.split(" ")]
    fragfn=lambda name,frag: 1 if frag in name else 0
    namefn=lambda name,list: True if not len(list) \
                             else reduce(lambda x,y:x+y, \
                                         [fragfn(name,frag) for frag in list])
    return lambda name: namefn(name.lower(), fragments)

