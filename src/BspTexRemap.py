''' BspTexRemap.py
    the main compiler command line app
'''
from bsptexremap import consts
from bsptexremap.enums import DumpTexInfoParts
from bsptexremap.materials import MaterialSet, TextureRemapper
from bsptexremap.utils import *
from bsptexremap.bsputil import *
from bsptexremap.common import *
from argparse import ArgumentParser
from jankbsp import BspFileBasic as BspFile
from pathlib import Path
import logging


def parse_arguments():
    ''' parse command line arguments and returns the parsed data
    '''
    parser = ArgumentParser(add_help=False)
    
    # flags and switches (takes no value)
    parser.add_argument(
        "-h", "-help", action="help",
        help="show this help message and exit",
    )
    
#    parser.add_argument(
#        "-low", action="store_const", dest="priority", const="low",
#        help="set process priority level to low",
#    )
#    parser.add_argument(
#        "-high", action="store_const", dest="priority", const="high",
#        help="set process priority level to high",
#    )
    parser.add_argument(
        "-backup", action="store_true",
        help="makes backup of BSP file",
    )
    
    # arguments that take value
    loglevels = ["off"]+[l.lower() for l in logging.getLevelNamesMapping().keys()]
    loglevels.remove("notset")
    parser.add_argument(
        "-log", choices=loglevels, default="warning", # metavar="LEVEL",
        help="set logging level (default: %(default)s)",
    )
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
        # type=texinfo_type,
        help="outputs the edited BSP file here instead of overwriting",
    )
    
    # bsp path
    parser.add_argument(
        "bsppath", 
        help="BSP file to operate on",
    )
    return parser.parse_args()


def main():
    # parse arguments
    args = parse_arguments()
    print("----START----")
    
    # set log level
    setup_logger(args.log)
    log = logging.getLogger(__name__)
    
    # load bsp
    # with_suffix is required to be compatible with other compilers which omits 
    # the file extension
    bsppath = Path(args.bsppath).with_suffix(".bsp")
    print(f'Loading bsp file: "{bsppath}"')
    with open(bsppath, "r+b") as f:
        bsp = BspFile(f)
    
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

    
if __name__=="__main__":
    print(consts.APP_HEADER)
    result = main()
    print("-----END-----")
    exit(result)
