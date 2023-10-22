''' BspTexRemap.py
    the main compiler command line app
'''
from bsptexremap import consts
from bsptexremap.enums import DumpTexInfoParts
from bsptexremap.materials import MaterialConfig, MaterialSet, TextureRemapper
from bsptexremap.utils import *
from bsptexremap.bsputil import *
from bsptexremap.common import * # parse_arguments etc
from jankbsp import BspFileBasic as BspFile
from pathlib import Path
import logging, tomllib

def process_bsp(cfg, args):
    # load bsp
    # with_suffix is required to be compatible with other compilers which omits 
    # the file extension
    bsppath = Path(args.bsppath).with_suffix(".bsp")
    print(f'Loading bsp file: "{bsppath}"')
    with open(bsppath, "r+b") as f:
        bsp = BspFile(f)
        
    # configure MaterialConfig with the entries from the cfg
    # then setup it for the current game, which sets MaterialSet.MATCHARS appropriately
    # we need to do this before dump_texinfo which now uses MaterialConfig 
    # to get the material names
    MaterialConfig.config(cfg["Materials"])
    MaterialConfig.setup(bsp_modname_from_path(bsppath))
    
    # texinfo dump zenpen (embedded/external/grouped)
    if args.dump_texinfo:
        texinfo_parts = flag_str_parser(DumpTexInfoParts)(args.dump_texinfo)
        dump_texinfo(bsppath, 3072|(texinfo_parts&7), bsp)
    
    # look for materials path
    matpath = search_materials_file(bsppath, bsp.entities,
            getattr(args, consts.CMDLINE_MATPATH_KEY)
    )
    if not matpath:
        log.critical("No materials.txt to read.")
        return 1 # error
    print(f'Found materials.txt file: "{matpath}"')

    # setup materials for the current game, which sets MaterialSet.MATCHARS appropriately
    MaterialConfig.setup(bsp_modname_from_path(matpath))
    
    # load THE materials set
    material_set = MaterialSet.from_materials_file(matpath)
    print(f'{len(material_set):>3d} entries read from materials file.')
    infolog_material_set(material_set)
    
    # get the choice cut
    choice_set = +material_set
    print(f'{len(choice_set):>3d} entries available for our great hack.')
    infolog_material_set(choice_set)
    
    # texinfo dump kouhen (unique texgroups)
    if args.dump_texinfo:
        dump_texinfo(bsppath, texinfo_parts&8, bsp, material_set)
    
    # loads wannabe sets
    print("Loading texture remap entries...")
    wannabe_set = load_wannabe_sets(bsp, bsppath, \
            getattr(args, consts.CUSTOMMAT_ARG), not args.custommat_read_all)
    if not len(wannabe_set):
        print("No texture remap entries found. Nothing to do.")
        return 0
    print(f'{len(wannabe_set)} texture remap entries.')
    infolog_material_set(wannabe_set)
    
    # backup bsp now
    if args.backup: 
        backup_file(bsppath)
    
    # go ahead and rename them textures
    # there's a fn for this in bsputil but I want to make it happen in main
    print("Renaming textures now...")
    remapperfn = TextureRemapper(wannabe_set, choice_set)
    succ_count, fail_count = 0,0
    for miptex in bsp.textures_m:
        newname = remapperfn(miptex.name)
        if newname and newname.lower() != miptex.name.lower():
            log.info(f"{miptex.name:15s} --> {newname}")
            miptex.name = newname
            succ_count += 1
        else:
            log.info(f"{miptex.name:15s} --> (unchanged)")
            fail_count += 1
    print(f"Success count: {succ_count}")
    print(f"Failure count: {fail_count}")
    if not succ_count:
        print("No changed made to texture names. Exiting.")
        return 0
    
    # write to file
    outpath = Path(args.outpath) if args.outpath else bsppath
    print(f"Writing changes to file: {outpath.name}")
    with open(outpath, "wb") as f:
        bsp.dump(f)
    
    # END OF MAIN
    return 0


def main():
    print(consts.APP_HEADER)
    # load cfg
    cfgpath = get_base_path().with_name("BspTexRemap.cfg.toml")
    cfg = tomllib.loads(Path(cfgpath).read_text())
    # parse arguments
    args = parse_arguments()
    
    # set log level
    setup_logger(args.log)
    log = logging.getLogger() ## "__main__" should use the root logger
    print("----START----")
    result = process_bsp(cfg,args)
    print("-----END-----")
    return result
    
if __name__=="__main__":
    result = main()
    exit(result)
