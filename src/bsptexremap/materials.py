''' materials.py
    classes that deal with materials go here
'''
from . import consts #, common
from .utils import char_padder
from .enums import MaterialEnum
#from .common import modpath_fallbacks
import re
from pathlib import Path
from typing import ClassVar
from collections import namedtuple
from logging import getLogger
log = getLogger(__name__)


class TextureRemapper:
    ''' creates a callable instance, that returns a remapped texname as specified
        in the initial target and choice MaterialSets,
        target_set being the texnames that wanted to be the specified material,
        choice_Set being the set with the valid entries from materials.txt,
        map_dict being direct map, no questions asked

        sample usage:
        >>> tm = TextureRemapper(wannabe_set, choice_set)
        >>> for miptex in bsp.miptexes:
        >>>     miptex.name = tm(miptex.name)
        or
        >>> newnames = list(map(tm, oldnames))
    '''
    def __init__(self, target_set, choice_set, map_dict={}):
        self.target_set = target_set
        self.choice_set = choice_set
        self.map_dict = {k.upper():v for k,v in map_dict.items()}
        self.groupmap = {} # tracks group names, so it returns the same remapped names
        self.iterators = dict({m:{} for m in MaterialSet.MATCHARS})

    def get_iterator(self, mat:str, targetlen:int):
        ''' returns the appropriate iter_padded_names for specified mat and len
            (creating the iterators on the fly as needed)
        '''
        log.debug("mat: %s, targetlen: %d", mat, targetlen)
        self.iterators.setdefault(mat, {})
        return self.iterators[mat].setdefault(
            targetlen,
            self.choice_set.iter_padded_names(mat,targetlen)
        )

    def __call__(self, texname:str) -> str:
        ''' the call method of the instance
        '''
        parts = re.match(consts.TEX_PARTS_RE, texname)
        # IMPORTANT: material set consistently populated with uppercase values
        texgroupname = parts["texname"].upper()

        if texgroupname in self.map_dict:
            log.debug("%s found in dict", texgroupname)
            return parts["prefix"] + self.map_dict[texgroupname]

        elif texgroupname not in self.target_set \
        or re.match(consts.TEX_IGNORE_RE, texname) \
        or len(parts["prefix"]) > 2:
            log.debug("%15s (%15s) fails check: %s|%s|%s",
                      texgroupname, texname,
                      texgroupname not in self.target_set,
                      re.match(consts.TEX_IGNORE_RE, texname),
                      len(parts["prefix"]) > 2 )
            return texname

        elif texgroupname in self.groupmap:
            log.debug("%s in group", texgroupname)
            return parts["prefix"] + self.groupmap[texgroupname]

        targetmat = self.target_set.get_mattype_of(texgroupname)
        targetlen = consts.TEXNAME_MAX_LEN - len(parts["prefix"])
        result = next(self.get_iterator(targetmat,targetlen), None)
        if not result: # exhausted available names for this mattype+len combo
            log.debug(f"{texgroupname} ran out of material names")
            return texname # unchanged

        if parts["grouped"]:
            self.groupmap[texgroupname] = result

        log.debug(f"%15s -> %s", texgroupname, result)
        return parts["prefix"] + result


class MaterialConfig:
    ''' class-var to hold material configuration from the cfg.toml file
        setup() interacts with MaterialSet, setting its MATCHARS
    '''
    _config  : ClassVar[dict] = None
    _cur_cfg : ClassVar[dict] = None
    current_game : ClassVar[str] = None

    @classmethod
    def config(cls, config):
        ''' configure the class with the entries from the TOML file.
            this should allow us to dynamically set MATCHARS by passing the game
            name to setup() classmethod
        '''
        cls._config = config

        return cls

    @classmethod
    def _get_cfg(cls, game:str):
        return next((item for item in cls._config \
                     if item["game"].lower() == game.lower()), None)

    @classmethod
    def setup(cls, game="valve", modpath=None):
        ''' sets up the class for the appropriate game by parsing the
            TOML-loaded config and recursively load the matchars as well as
            finding the default material.
        '''
        def _get_matchars(cfgitem):
            base = _get_matchars(cls._get_cfg(cfgitem["base"])) \
                    if "base" in cfgitem else ""
            return base + "".join(cfgitem["names"].keys())

        def _get_def_mat(cfgitem):
            return cfgitem["default_material"] \
                if "default_material" in cfgitem \
                else _get_def_mat(cls._get_cfg(cfgitem["base"]))

        if modpath:
            # if given modpath, try to follow the fallbacks until one with entry is found
            for cur_path in common.modpath_fallbacks(modpath):
                if (this_cfg := cls._get_cfg(cur_path.name)): break
            if not this_cfg: this_cfg = cls._get_cfg("valve") # final fallback
        else:
            this_cfg = cls._get_cfg(game) or cls._get_cfg("valve")
        cls._cur_cfg  = this_cfg
        cls.current_game = this_cfg["game"]

        MaterialSet.MATCHARS = _get_matchars(this_cfg)
        MaterialSet.DEF_MAT  = _get_def_mat(this_cfg)

        log.debug("MaterialConfig set up for game: %s", cls.current_game)
        
        return cls

    @classmethod
    def get_material_names_mapping(cls, game:str=None):
        ''' sidestepping the MaterialEnum by reading names as defined in TOML
            config file
        '''
        if cls._cur_cfg is None: cls.setup()
        
        this_cfg = cls._get_cfg(game) if game else cls._cur_cfg

        base = cls.get_material_names_mapping(this_cfg["base"]) \
               if "base" in this_cfg else {}

        return base | this_cfg["names"] if "names" in this_cfg else base

    @classmethod
    def get_material_colors(cls, game=None):
        ''' sidestepping MaterialColors by reading colors as defined in TOML
            config file
        '''
        if cls._cur_cfg is None: cls.setup()

        this_cfg = cls._get_cfg(game) if game else cls._cur_cfg
                        
        result = cls.get_material_colors(this_cfg["base"]) \
                 if "base" in this_cfg else {}
        if "colors" in this_cfg:
            result |= this_cfg["colors"]

        _c = namedtuple("ColorRegistry", ["color","bg","fg"])
        return {m:_c(*val) for m,val in result.items()}
    
    @classmethod
    def get_games_list(cls):
        return [x["game"] for x in cls._config if "game" in x]


class MaterialSet(dict):
    ''' class for parsing, processing, and outputting goldsrc material lists.

        use MaterialConfig.config() to load information from the TOML file about
        matchars available per game, then use MaterialConfig.setup() to setup
        the matchars for the selected game.
    '''

    # change this value if working with OF|CZ|CZDS
    # (though only OF seem to support the hack)
    MATCHARS : ClassVar[str]  = "CMDVGTSWPYF"
    DEF_MAT  : ClassVar[str]  = "C"

    @classmethod
    def strip(cls, instr:str) -> str:
        ''' helper fn that strips prefixes from texture names, forming a proper
            material name
        '''
        m = re.match(consts.TEX_PARTS_RE, instr)
        return m["texname"] if m else instr


    def __init__(self, **kwargs):
        for mat in self.__class__.MATCHARS:
            super().update({mat: set(kwargs[mat]) if mat in kwargs else set()})


    @classmethod
    def from_materials_file(cls, file):
        self = cls()
        log.info(f"Reading materials file: {file}")
        report_incompat = 0
        with open(file, "r") as f:
            for line in f.readlines():
                parts = line.split("//", 1)[0].split(" ",2)
                if len(parts) < 2: continue

                matchar, matname = parts[0].strip(), cls.strip(parts[1])
                if not len(matchar) or matchar not in cls.MATCHARS:
                    log.warning("read unknown material type %s", matchar)
                    continue
                # matname not matching read entry indicates prefixes in entries
                if len(matname) != len(parts[1].strip()):
                    report_incompat += 1

                self[matchar.upper()].add(matname.upper())

        if report_incompat:
            log.warning("%d entries found with prefixes. This may mean that the mod doesn't support the texture name hack, and the texture remappings may not work.",report_incompat)

        return self

    @classmethod
    def from_entity(cls, ent):
        self = cls()

        for k, v in ent.items():
            if re.match(consts.ENT_PROPS_RE, k) \
            or re.match(consts.TEX_IGNORE_RE,k) \
            or len(v) != 1: continue

            self[v.upper()].add(cls.strip(k.upper()))

        return self

    def get_mattype_of(self, texgroupname:str) -> str:
        ''' returns the name of the material set containing texgroupname '''
        texgroupname = MaterialSet.strip(texgroupname)
        for m in MaterialSet.MATCHARS:
            if texgroupname in self[m]:
                return m

    def iter_padded_names(self, mat:str, targetlen:int) -> str:
        ''' generator that yields a name from the target material padded with
            random chars of given length.
            client code should account for different lengths of the textures
            they're replacing.
            also, only call this on a choice cut instance of the class
            usage:
                g = MaterialSet.iter_padded_names(mat, len)
                newname = next(g,None)
        '''
        for texgroupname in sorted(self[mat]):
            for padstr in char_padder(targetlen - len(texgroupname)):
                yield texgroupname + padstr

    def __getitem__(self, item):
        ''' support for instance[mattype] '''
        return super().get(item)# or None

    def __contains__(self, texgroupname:str):
        ''' check if texgroupname is in any of the material sets '''
        return True if self.get_mattype_of(texgroupname) else False

    def __len__(self):
        ''' reports the combined number of entries across all material sets '''
        sum = 0
        for m in self.__class__.MATCHARS:
            sum += len(self[m])
        return sum

    def asdict(self):
        ''' this purposefully enumerates by the class internal MATCHARS so that
            we don't over-report sets in OF/CS/CZ/DS otherwise not supported in vanilla
        '''
        return {m:self[m] for m in self.__class__.MATCHARS}

    def astuple(self):
        return tuple(super().values())

    @property
    def sets(self):
        ''' iterates through all sets in this object where the type of material
            doesn't matter, only that it's here somewhere.
            an example is to remove texture names already in given materials.txt
        '''
        return self.astuple()

    def choice_cut(self):
        ''' returns a subset with suitable names (length between 12 and 14)
            special case for "C": add "__CONCRETE" to it
        '''
        concrete_admix = {"__CONCRETE"}
        cutfn = lambda tex: consts.MATNAME_MIN_LEN <= len(tex) <= consts.TEXNAME_MAX_LEN-1
        mapfn = lambda mat,vals: concrete_admix | vals \
                                 if mat == self.__class__.DEF_MAT \
                                 else set(filter(cutfn,vals))

        return MaterialSet(**{
                m:mapfn(m,self[m]) for m in MaterialSet.MATCHARS
        })


    ''' ARITHMETIC OPERATION SUPPORT -------------------------------------------
        this allows us to use arithmetic operations between two instances of MaterialSet
        NOTE: since we're dealing with set we use set operations (union/diff)
            Set1 | Set2, Set1 |= Set2   # unions
            Set1 - Set2, Set1 -= Set2   # diffs
            +Set                        # choice cut of Set (12>len>15)
    ''' ##----------------------------------------------------------------------
    def __or__(self, other): # self | other
        ''' union of two instances into a third '''
        return MaterialSet(**{m:self[m] | other[m] for m in MaterialSet.MATCHARS})

    def __sub__(self, other): # self - other
        ''' diff two instances into a third
            e.g. removing map entries already in materials.txt
        '''
        return MaterialSet(**{m:self[m] - other[m] for m in MaterialSet.MATCHARS})

    def __ior__(self, other): # self |= other
        ''' unite other to self '''
        for m in MaterialSet.MATCHARS: self[m].update(other[m])
        return self

    def __isub__(self, other): # self -= other
        ''' diff other from self '''
        for m in MaterialSet.MATCHARS: self[m].difference_update(other[m])
        return self

    def __pos__(self): # +self
        ''' alias to choice_cut '''
        return self.choice_cut()

