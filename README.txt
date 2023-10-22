BspTexRemap
 version 0.3
 (c) M Faiz Syahmi @ kimilil, 2023

ABOUT
=====
This program patches a BSP file, replacing names of embedded textures to those
in a given materials.txt, to try and eliminate the need to edit or ship a
modified materials.txt, thus increasing map portability.
The match and replacement textures are defined in a info_texture_remap entity
placed in the map, or in a "<mapname>_custommat.txt" alongside the map file,
or supplied in an external file.


USAGE
=====
usage: BspTexRemap.exe [-h] [-backup]
                       [-log {off,critical,fatal,error,warn,warning,info,debug}]
                       [-dump_texinfo {embedded,external,grouped,uniquegrouped}]
                       [-materials_path MATERIALS_PATH]
                       [-custommat_path CUSTOMMAT_PATH] [-custommat_read_all]
                       [-out OUTPATH]
                       bsppath

positional arguments:
  bsppath               BSP file to operate on

options:
  -h, -help             show this help message and exit
  -backup               makes backup of BSP file
  -log {off,critical,fatal,error,warn,warning,info,debug}
                        set logging level (default: warning)
  -dump_texinfo {embedded,external,grouped,uniquegrouped}
                        creates a file with names of textures used in the map
                        (you can mix the values with + sign, no spaces)
  -materials_path MATERIALS_PATH
                        target game/mod's materials.txt file
  -custommat_path CUSTOMMAT_PATH
                        file with custom texture material remappings
  -custommat_read_all   combine all given/available custom texture material
                        remappings, otherwise stops when found entries from a
                        source, in this order: info_texture_remap ->
                        bspname_custommat.txt -> custommat_path
  -out OUTPATH          outputs the edited BSP file here instead of
                        overwriting


There's also BspTexRemap_GUI.exe, a GUI program that lets you view textures in GoldSrc BSP files, including external WAD textures, loads materials.txt, assigns custom materials to the textures in the BSP, exports and imports _custommat.txt files, and commit changes to BSP files. 

LICENSE
=======
 (c) M Faiz Syahmi @ kimilil, 2023
 Released under MIT License (MIT)

  see BspTexRemap_license.txt for full license text.


F.A.Q. (Fairly Anticipated Questions)
=====================================
See FAQ.txt


SPECIAL THANKS
==============
- Bernhard Manfred Gruber for the format specs at the hlbsp project: https://hlbsp.sourceforge.net/index.php
- @nein_ at Discord for daring to test my broken af program
- The TWHL community
