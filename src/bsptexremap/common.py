''' common.py
    all common functions go here.
    basically whatever functionality a command shell program and a compiler
    program would have in common.
'''
from . import consts
from .enums import DumpTexInfoParts, MaterialEnum # dump_texinfo
from .utils import *
from .bsputil import *
from .materials import MaterialConfig, MaterialSet, TextureRemapper

# get_textures_from_wad
from jankbsp import WadFile
from jankbsp.types.wad import WadMipTex

import re, sys
from argparse import ArgumentParser
from pathlib import Path, PurePath
from shutil import copy2 as filecopy # backup_bsp
from functools import reduce
from logging import getLogger
log = getLogger(__name__)

def parse_arguments(gui=False):
    ''' parse command line arguments and returns the parsed data
    '''
    if gui:
        parser = ArgumentParser(
            add_help=False,
            description="This is a GUI program that takes a minimal number of command line arguments. Please run the CLI program for compile work, which functions fully with command line arguments."
        )
    else:
        parser = ArgumentParser(add_help=False)

    ## flags and switches (takes no value) -------------------------------------
    parser.add_argument(
        "-h", "-help", action="help",
        help="show this help message and exit",
    )

    if not gui:
        parser.add_argument(
            "-backup", action="store_true",
            help="makes backup of BSP file",
        )

    ## arguments that take value -----------------------------------------------
    loglevels = ["off"]+[l.lower() for l in logging.getLevelNamesMapping().keys()]
    loglevels.remove("notset")
    parser.add_argument(
        "-log", choices=loglevels, default="warning", # metavar="LEVEL",
        help="set logging level (default: %(default)s)",
    )

    if not gui:
        # texinfo_type = flag_str_parser(DumpTexInfoParts)
        texinfo_meta = f"{{{','.join([e.name.lower() for e in DumpTexInfoParts])}}}"
        parser.add_argument(
            "-dump_texinfo", metavar=texinfo_meta, default=0,
            # type=texinfo_type,
            help="creates a file with names of textures used in the map (you can mix the values with + sign, no spaces)",
        )
        parser.add_argument(
            f"-{consts.CMDLINE_MATPATH_KEY}", # use the const to standardize it
            help="target game/mod's materials.txt file",
        )
        parser.add_argument(
            f"-{consts.CUSTOMMAT_ARG}",
            help="file with custom texture material remappings",
        )
        parser.add_argument(
            f"-custommat_read_all", action="store_true",
            help=f"""
    combine all given/available custom texture material remappings, otherwise stops when found entries from a source, in this order:\n{consts.TEXREMAP_ENTITY_CLASSNAME} -> bspname{consts.CUSTOMMAT_SUFFIX}{consts.CUSTOMMAT_FMT} -> {consts.CUSTOMMAT_ARG}
            """.strip(),
        )
        parser.add_argument(
            "-out", metavar="OUTPATH", dest="outpath",
            help="outputs the edited BSP file here instead of overwriting",
        )

    # bsp path
    if gui:
        # optional for GUIs
        parser.add_argument("bsppath", nargs="?",
                help="BSP file to open",
        )
        parser.add_argument("-dev",action="store_true",help="dev mode")
    else:
        # required for CLI
        parser.add_argument("bsppath",
                help="BSP file to operate on",
        )

    return parser.parse_args()


def setup_logger(level:str|int):
    level = logging.getLevelName(level.upper())

    con_formatter = logging.Formatter(fmt='%(levelname)-8s: %(message)s')

    con_handler = logging.NullHandler if level in ["off", "0"] \
            else logging.StreamHandler(sys.stdout)
    con_handler.setFormatter(con_formatter)
    con_handler.setLevel(level)

    root_logger = logging.getLogger()
    root_logger.setLevel(0)
    root_logger.addHandler(con_handler)

    log.debug(f"log level set to {root_logger.getEffectiveLevel()}")


def get_base_path():
    ''' alternative to __file__ on __main__ that takes into account
        code compiled by pyinstaller or nuitka
    '''
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        #running in a PyInstaller bundle
        return Path(sys.argv[0])
    elif "__compiled__" in globals():
        #running in nuitka bundle
        return Path(sys.argv[0])
    else:
        #running in a normal Python process
        return Path(sys.modules["__main__"].__file__)


def matchars_by_mod(modname:str):
    return consts.MATCHARS_BY_MOD[modname.lower()] \
    or consts.MATCHARS_BY_MOD.valve


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
        if consts.TEXREMAP_MATPATH_KEY in ent:
            # skip entities where this key has empty value
            if not len(ent[consts.TEXREMAP_MATPATH_KEY].strip()): continue
            log.info("Reading materials_path property from info_texture_remap entity")

            try:
                candidate_paths = [Path(ent[consts.TEXREMAP_MATPATH_KEY])]
            except: # error reading value from entity
                log.warn("Error reading materials_path value from this entity. skipping.")
                continue # skip

            if not candidate_paths[0].is_absolute():
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


def search_wads(bsp_path, wadlist):
    ''' returns a dict of the search result:
        key being wad name and value being path if found, or None
        wadlist items will be popped once found, using its length to track progress
    '''
    bsp_path = Path(bsp_path)
    result = {wad:None for wad in wadlist} # initialize to all None (not found)
    counter = 0

    if bsp_path.parent.name.lower() == "maps":
        log.info("Trying to find wad files relative to map...")
        for modpath in modpath_fallbacks(bsp_path.parents[1]):
            if counter == len(wadlist): break # already found everything
            log.info(f"looking in {modpath}")
            for wad in wadlist:
                if result[wad]: continue # already found this one
                candidate = modpath / wad
                if candidate.exists():
                    log.info(f"found {wad} in {modpath}!")
                    result[wad] = candidate
                    counter += 1
    return result


def load_wannabe_set_from_bsp_entities(bsp):
    wannabe_set = MaterialSet()
    for texremap_ent in iter_texremap_entities(bsp.entities):
        wannabe_set |= MaterialSet.from_entity(texremap_ent)
    return wannabe_set


def load_wannabe_sets(bsp,bsppath,arg_val,first_found=True):
    ''' loads the wannabe sets in order:
        1. info_texture_remap entries
        2. bspname_custommat.txt
        3. argparse value
        if first_found, will stop loading as soon as the set has entries
    '''
    wannabe_set = MaterialSet()

    for step in range(3):
        if step == 0:
            for texremap_ent in iter_texremap_entities(bsp.entities):
                wannabe_set |= MaterialSet.from_entity(texremap_ent)
        elif step == 1:
            if bsp_custommat_path(bsppath).exists():
                wannabe_set |= MaterialSet\
                .from_materials_file(bsp_custommat_path(bsppath))
        elif step == 2:
            if arg_val and Path(arg_val).exists():
                wannabe_set |= MaterialSet.from_materials_file(arg_val)

        if first_found and len(wannabe_set): break

    return wannabe_set


def load_material_remaps_from_entity(entity):
    ''' given item_texture_remap entity, returns the hard remap entries
        e.g. "originalname" = "newname"
    '''
    return {k:v for k,v in entity.items() \
            if  not re.match(consts.ENT_PROPS_RE, k) \
            and not re.match(consts.TEX_IGNORE_RE,k) \
            and     len(v) > 1
    }


def dump_texinfo(bsppath,
                 parts: DumpTexInfoParts|int,
                 bsp,
                 material_set=None,
                 outpath=None,
                 **kwargs):
    ''' parts:
        1 - embedded
        2 - external
        4 - grouped (i.e. all texture group names)
        8 - uniquegrouped (i.e. all texture group names not in materials.txt)
        1024 - header
        2048 - material names
        4096 - material_set

        parts & 8 uses material_set to get the unique groups
        parts & 4096 dumps the material_set (useful to dump wannabe_set)
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
    me = MaterialConfig.get_material_names_mapping()
    mode = "w" if parts&1024 else "a"
    if not outpath:
        outpath = bsp_texinfo_path(bsppath)

    with open(outpath, mode) as f:
        log.info(f"Dumping texture info for {bsppath.name} --> {outpath.name}")

        if parts&1024: # header
            f.write(consts.TEXINFO.HEADER.format(
                    bsppath.name,
                    f"{consts.APPNAME} {consts.VERSION}"
            ))

        if parts&2048: # list of materials
            f.write("\n// Material types: \n")
            f.write("\n".join([f"//  {m} - {me[m]}" for m in MaterialSet.MATCHARS]))
            f.write("\n// (this list may not be exhaustive. consult the target mod's materials.txt)\n\n")

        if parts&4096: # material set
            f.write("\n// Material entries: ")
            # write down all the loaded wads (to be loaded later on load)
            if "wadlist" in kwargs and isinstance(kwargs["wadlist"], list):
                f.write(f"\n// wads: {','.join(kwargs['wadlist'])}")

            for m in material_set.MATCHARS:
                if not len(material_set[m]): continue # skip empty sets
                f.write(f"\n//  {m} - {me[m]}\n")
                f.write("\n".join([f"{m.upper()} {item.upper()}" \
                        for item in sorted(material_set[m]) ]) )

        for thispart in filter(lambda f:parts&f, [1,2,4,8]):
            log.info(f"Dumping texture list {e(thispart).value}: {e(thispart).name}")
            f.write(consts.TEXINFO.SECTION.format( e(thispart).name.upper() ))
            f.write("\n".join(sorted(valuegetter[thispart](bsp,material_set))) + "\n")


def filter_materials(source, matchars, names):
    ''' for the gui '''
    l = lambda x:x.lower()
    matfn =lambda mat: not len(matchars) or mat in matchars.upper()
    namefn=lambda name,list:not len(list) or any((l(frag) in l(name) for frag in list))

    fragments = [x for x in names.split(" ") if len(x)]
    result = MaterialSet()
    for mat in source.MATCHARS:
        if not matfn(mat): continue # empty if material not match
        filtered = set(name for name in source[mat] if namefn(name,fragments))
        result[mat].update(filtered)

    return result


def get_textures_from_wad(wadpath:str|Path, texture_names:str) -> tuple[dict,list]:
    ''' loads miptexes of any of the textures in texture_names found in wad file.
        this is so that we only read miptexes referenced in bsp file.

        returns a tuple of the miptexes and a list of all textures.
        the latter would be used to check that unembedding textures don't leave
        orphans
    '''
    texture_names = [x.lower() for x in texture_names]
    result = {}

    with open(wadpath, "rb") as fp:
        wad = WadFile.load(fp, True)
        for item in wad.entries:
            if item.name.lower() not in texture_names: continue
            # log.debug(f"{item.name} is wanted and found")
            fp.seek(item.offset)
            result[item.name] = WadMipTex.load(fp,item.sizeondisk)

    return (result, tuple((item.name for item in wad.entries)))


def backup_file(filepath:Path|str):
    ''' backup given file by giving it the ".bak" extension '''
    filepath = Path(filepath)
    bakpath = filepath.with_name(filepath.name + ".bak")
    if not bakpath.exists():
        filecopy(filepath, bakpath)

