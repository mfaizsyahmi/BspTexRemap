#import PyInstaller.__main__
import sys, compileall, subprocess, shutil, argparse, tomllib
from pathlib import Path
from time import sleep
try:
    from bsptexremap.consts import APPNAME, VERSION
except:
    APPNAME, VERSION = "BspTexRemap", "_dev"
    
## check that we're running in a venv
if sys.prefix == sys.base_prefix:
    print("This script must be run in a venv!")
    sys.exit(1)

## CONSTS
CFGPATH = Path(__file__).with_suffix(".cfg.toml")
basepath = Path(__file__).parent


matrix = {
    "CLI" : [
        'BspTexRemap.py'
    ],
    "GUI" : [
        '--windowed',
        '-i', './assets/images/BspTexRemap_64.ico',
        'BspTexRemap_GUI.py',
    ]
}


## check that there's no errors in the files
def compile_sources():
    print("Checking source files for errors")
    compile_dirs = [
        basepath / "jankbsp",
        basepath / "DearPyGui_LP",
        basepath / "bsptexremap",
    ]
    for dir in compile_dirs:
        if not compileall.compile_dir(str(dir)):
            print(f"{dir.name} has errors! aborting.")
            sys.exit(1)
    for item in matrix.values():
        if not compileall.compile_file(basepath / item[-1]):
            print(f"{item[-1]} has errors! aborting.")
            sys.exit(1)
    print("Source file check done.")


## start the bundler subprocesses
def run_bundlers():
    ## common bundler arguments 
    common_args = [
        '--paths', 'venv/lib/site-packages',
        '--workpath', '../build',
        '--distpath', '../dist',
        '--clean',
        '--noconfirm'
    ]
    
    # start subprocesses
    procmap = {}
    for label, item in matrix.items():
        print(f"Starting bundler subprocess: {label}")
        procmap[label] = subprocess.Popen(
                ["PyInstaller"] + common_args + item, 
                creationflags=subprocess.CREATE_NEW_CONSOLE
        )

    # wait for subprocesses to finish
    done_part = set()
    while len(done_part) < len(procmap):
        for label, proc in procmap.items():
            proc.poll()
            if proc.returncode is not None:
                done_part.add(label)
                print(f"{label} exited with code: {proc.returncode}")
        sleep(1)

    return procmap


def integrate_assets(procmap=None):
    if procmap and procmap["GUI"].returncode > 0:
        print("GUI bundling failed. cannot integrate.")

    print("Integrating into a single dist folder...")
    
    # copies over assets
    destpath = basepath.parent / "dist/BspTexRemap_GUI"
    for name in ["BspTexRemap.cfg.toml", 
                 "BspTexRemap_GUI.layout.ini", 
                 "assets"]:
    
        source = basepath / name
        destination = destpath / name
        
        if source.is_dir():
            shutil.copytree(source,destination, dirs_exist_ok=True)
        else:
            shutil.copy(source,destination)
    
    # copies over the CLI program to the GUI bundle 
    cli_src = basepath.parent / "dist/BspTexRemap/BspTexRemap.exe"
    cli_dest = destpath / "BspTexRemap.exe"
    shutil.copy(cli_src,cli_dest)
    
    # copies over readmes/fgds to dist folder
    destpath = basepath.parent / "dist"
    for glob in ["*.txt", "*.fgd"]:
        for srcfile in basepath.parent.glob(glob):
            shutil.copy(srcfile, destpath/srcfile.name)

    print("Asset integration done.")
    

def zip_dist(exe7zip_path):
    print("Zipping up distribution...")
    
    cwd = basepath.parent
    destzip = cwd / f"{APPNAME}_{VERSION[1:]}_win_x64.zip"
    
    # remove existing zip with same name
    if destzip.exists():
        print(f"Removing existing zip file {destzip.name}")
        destzip.unlink()
    
    # run 7zip, adding everything
    subprocess.run([
        exe7zip_path,
        'a',            # add
        destzip.name,   # target zip file
        r'.\dist\*',    # everything in dist (but dist will not be included in zip path)
        r'-x!.\dist\BspTexRemap', # exclude the CLI dir
#        '-mcp=utf-8',    # use utf8 encoding for file names
        '-mx9',          # ultra compression
    ], cwd=cwd)
    # run 7zip a second time to rename BspTexRemap_GUI folder to just BspTexRemap
    subprocess.run([
        exe7zip_path,
        'rn',           # rename
        str(destzip),   # target zip file
        "BspTexRemap_GUI", "BspTexRemap", 
    ], cwd=cwd)
    
    print("Zipping done.")


def parse_arguments():
    parser = argparse.ArgumentParser()
    
    compile_arg = parser.add_mutually_exclusive_group()
    compile_arg.add_argument(
        "-s", "--compile_sources", 
        dest="compile_sources", action='store_true', default=True,
        help="Compile all sources to check for syntax errors (default)",
    )
    compile_arg.add_argument(
        "-S", "--no_compile_sources",
        dest="compile_sources", action='store_false',
        help="SKIP compiling sources",
    )

    bundle_arg = parser.add_mutually_exclusive_group()
    bundle_arg.add_argument(
        "-b", "--bundle_scripts", 
        dest="bundle_scripts", action='store_true', default=True,
        help="Bundle the main program scripts with PyInstaller (default)",
    )
    bundle_arg.add_argument(
        "-B", "--no_bundle_scripts", 
        dest="bundle_scripts", action='store_false',
        help="SKIP bundling main program scripts",
    )
    
    integration_arg = parser.add_mutually_exclusive_group()
    integration_arg.add_argument(
        "-i", "--integrate_assets", 
        dest="integrate_assets", action='store_true', default=True,
        help="Integrates assets and all programs to a sindle dist folder (default)",
    )
    integration_arg.add_argument(
        "-I", "--no_integrate_assets", 
        dest="integrate_assets", action='store_false',
        help="SKIP integrating assets",
    )

    zip_arg = parser.add_mutually_exclusive_group()
    zip_arg.add_argument(
        "-z", "--zip_dist", 
        dest="zip_dist", action='store_true', default=True,
        help="Zips the distribution folder (default)",
    )
    zip_arg.add_argument(
        "-Z", "--no_zip_dist", 
        dest="zip_dist", action='store_false', 
        help="SKIP zipping distribution",
    )
    
    return parser.parse_args()


def main():
    if CFGPATH.exists():
        cfg = tomllib.loads(CFGPATH.read_text())
    else:
        cfg = {}
    
    args = parse_arguments()
    print("Compile sources :", args.compile_sources)
    print("Bundle scripts  :", args.bundle_scripts)
    print("Integrate assets:", args.integrate_assets)
    print("Zip distribution:", args.zip_dist)
    
    if args.compile_sources:    
        compile_sources()
        
    if args.bundle_scripts:     
        procmap = run_bundlers()
    else: 
        procmap = None
        
    if args.integrate_assets:
        integrate_assets(procmap or None)
            
    if args.zip_dist:
        if "7zip_path" not in cfg:
            print(f"Cannot zip distribution: '7zip_path' not defined in {CFGPATH.name}")
        else:
            zip_dist(cfg["7zip_path"])


if __name__ == "__main__":
    main()

