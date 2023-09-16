''' common.py
    all common functions go here.
    basically whatever functionality a command shell program and a compiler
    program would have in common.
'''
from . import consts
from .enums import DumpTexInfoParts, MaterialEnum # dump_texinfo
from .utils import *
from .bsputil import *
from .materials import MaterialSet, TextureRemapper
import re, sys
from pathlib import Path, PurePath
from shutil import copy2 as filecopy # backup_bsp
from logging import getLogger
log = getLogger(__name__)

def setup_logger(level:str):
    formatter = logging.Formatter(fmt='%(levelname)-8s: %(message)s')
    handler = logging.NullHandler if level in ["off", "0"] \
            else logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(level.upper())
    root_logger.addHandler(handler)
    log.debug(f"log level set to {root_logger.getEffectiveLevel()}")


def modpath_fallbacks(modpath:Path) -> Path:
    ''' generator that yields mod paths, all the way to "valve"
        use cases:
        - searching for materials.txt
        - searching for wads
    '''
    modname = re.sub(consts.MODNAME_SUFFIX_RE, "", modpath.name)
    modbasepath = modpath.with_name(modname) # without suffix
    yield modpath # 1: the base input
    yield modbasepath # 2: path with suffix removed (might be the same as #1)

    # read liblist.gam and follow its fallback_dir
    liblist_path = modbasepath / "liblist.gam"
    liblist_text = liblist_path.read_text() if liblist_path.exists() else ""
    fallback_match = re.match(consts.LIBLIST_FALLBACK_RE, liblist_text)
    if fallback_match:
        fallback_path = modbasepath.parent / fallback_match["dir"]
        yield fallback_path # 3: fallback_dir as read in liblist.gam

    fallback_path = modbasepath.parent / consts.FALLBACK_OF_LAST_RESORT
    yield fallback_path # 4: valve folder (might be the same as #3)


def search_materials_file(bsp_path, bsp_entities=[], args_matpath=None):
    ''' search for materials file in this order of precedence:
		1 - entity's materials_path entry (relative to bsp_path or absolute)
		2 - cmd line entry
		3 - mod's, if map is in maps folder
		4 - fallback's, if liblist.gam can be found and read
    '''
    bsp_path = Path(bsp_path)

    # 1 - entity's materials_path entry
    ent_filter_fn = lambda ent: ent["classname"] == consts.TEXREMAP_ENTITY_CLASSNAME
    has_remap_entities = False # init
    for ent in filter(ent_filter_fn, bsp_entities):
        has_remap_entities = True
        if TEXREMAP_MATPATH_KEY in ent:
            log.info("Reading materials_path property from info_texture_remap entity")

            candidate_paths = [Path(ent[TEXREMAP_MATPATH_KEY])]
            if not candidate_path.is_absolute():
                candidate_paths.append(bsp_path / candidate_paths[0])
            for candidate in candidate_paths:
                if candidate.exists():
                    return candidate
    if has_remap_entities:
        log.warn("Couldn't find valid materials.txt path from entity")

    # 2 - cmd line entry
    if args_matpath:
        log.info("Read materials_path property from command line")
        candidate = Path(args_matpath)
        if candidate.exists():
            return candidate
        log.warn("Couldn't find valid materials.txt path from command line")

    # 3 - mod's, if map is in maps folder
    # 4 - fallback's, if liblist.gam can be found and read
    if bsp_path.parent.name.lower() == "maps":
        log.info("Trying to find materials.txt relative to map...")
        for modpath in modpath_fallbacks(bsp_path.parents[1]):
            if modpath.name.endswith("_downloads"): continue # don't look for it here
            log.info(f"Looking in '{modpath.name}' mode/game folder")
            candidate = modpath / "sound/materials.txt"
            if candidate.exists():
                return candidate

    log.warn("No materials.txt file found.")


def load_wannabe_sets(bsp,bsppath,arg_val,first_found=True):
    ''' loads the wannabe sets in order:
        1. info_texture_remap entries
        2. bspname_custommat.txt
        3. argparse value
        if first_found, will stop loading as soon as the set has entries
    '''
    wannabe_set = MaterialSet()

    for step in range(3):
        match step:
            case 0:
                for texremap_ent in iter_texremap_entities(bsp.entities):
                    wannabe_set |= MaterialSet.from_entity(texremap_ent)
            case 1:
                if bsp_custommat_path(bsppath).exists():
                    wannabe_set |= MaterialSet\
                    .from_materials_file(bsp_custommat_path(bsppath))
            case 2:
                if arg_val and Path(arg_val).exists():
                    wannabe_set |= MaterialSet.from_materials_file(arg_val)

        if first_found and len(wannabe_set): break

    return wannabe_set


def dump_texinfo(bsppath, parts: DumpTexInfoParts|int, bsp, material_set=None, **kwargs):
    ''' parts:
        1 - embedded
        2 - external
        4 - grouped (i.e. all texture group names)
        8 - uniquegrouped (i.e. all texture group names not in materials.txt)
        1024 - header
        2048 - material names
    '''
    if not parts: return

    def get_unique_grouped(bsp,matset):
        uniquetexgroups = list_texgroups(bsp.textures_m)
        uniquetexgroups.difference_update(*matset.sets)
        return uniquetexgroups

    valuegetter = {
        1:lambda bsp,matset:list_textures(bsp.textures_m),
        2:lambda bsp,matset:list_textures(bsp.textures_x),
        4:lambda bsp,matset:list_texgroups(bsp.textures), # all texgroups in map
        8:lambda bsp,matset:get_unique_grouped(bsp,matset)
    }

    e = DumpTexInfoParts # shorthand
    me = MaterialEnum # ditto
    mode = "w" if parts&1024 else "a"
    outpath = bsp_texinfo_path(bsppath)

    with open(outpath, mode) as f:
        log.info(f"Dumping texture info for {bsppath.name} --> {outpath.name}")
        if parts&1024:
            f.write(consts.TEXINFO.HEADER.format(
                    bsppath.name,
                    f"{consts.APPNAME} {consts.VERSION}"
            ))
        if parts&2048:
            f.write("\n// Material types: \n")
            f.write("\n".join([f"//  {m} - {me(m).name}" for m in MaterialSet.MATCHARS]) + "\n")

        for thispart in filter(lambda f:parts&f, [1,2,4,8]):
            log.info(f"Dumping texture list {e(thispart).value}: {e(thispart).name}")
            f.write(consts.TEXINFO.SECTION.format(e(thispart).name.upper()))
            f.write("\n".join(sorted(valuegetter[thispart](bsp,material_set))) + "\n")


def backup_file(filepath:Path|str):
    ''' backup given file by giving it the ".bak" extension '''
    filepath = Path(filepath)
    bakpath = filepath.with_name(filepath.name + ".bak")
    if not bakpath.exists():
        filecopy(filepath, bakpath)
