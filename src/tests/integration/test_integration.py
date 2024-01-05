''' I'm too lazy to write unit tests
'''
import unittest, subprocess, sys
from pathlib import Path
from shutil import copy2
# inject sys.path to be able to load jankbsp
sys.path.append(str(Path(__file__).parents[2]))
from jankbsp import BspFileBasic as BspFile
from jankbsp.types import EntityList

ALLTESTS = 0b11111111 # bitflags for tests to run
CAPTURE_OUTPUT = False # if true, redirect output away from terminal
LOG_LEVEL = "info"    # log level for app

class TestApp(unittest.TestCase):
    def setUp(self):
        # path to script file
        self.scriptpath = Path(__file__).parents[2] / "BspTexRemap.py"
        # path to fixtures path
        self.fixturepath = Path(__file__).parent / "fixtures_mod"

        self.bsppath = self.fixturepath / "maps/dm_hellhole.bsp"
        self.bsppath_origin = self.bsppath.with_suffix(".ORIGIN") # MUST EXIST
        self.bsppath_other = self.fixturepath / "maps/output.bsp"

        self.texinfopath = self.fixturepath / "maps/dm_hellhole_texinfo.txt"

        self.custommatpath = self.fixturepath / "maps/dm_hellhole_custommat.txt"
        self.custommatpath_origin = self.custommatpath.with_suffix(".NOPE") # MUST EXIST

        self.entpath = self.fixturepath / "maps/extras.ent" # MUST EXIST

        self.materials_path = r"D:\SteamLibrary\steamapps\common\Half-Life\valve\sound\materials.txt" # MUST EXIST

        copy2(self.bsppath_origin, self.bsppath)

    def tearDown(self):
        for deleteme in [
                self.bsppath,
                self.texinfopath,
                self.custommatpath,
                self.bsppath_other
        ]:
            try: deleteme.unlink()
            except FileNotFoundError: pass
    
    def subTestTexgroup(self, target_bsp=None):
        ''' subtest to check that every +A names has at least the +0 equivalent
        '''
        if not target_bsp: target_bsp = self.bsppath
        with open(target_bsp, "r+b") as f:
            bsp = BspFile(f)
        texnames = [miptex.name.lower() for miptex in bsp.textures_m]
        for plus_a_name in filter(lambda n: n[0:2] == "+a",texnames):
            self.assertTrue("+0" + plus_a_name[2:] in texnames)

    # @unittest.skip
    @unittest.skipIf(not ALLTESTS & 1, "skip flag")
    def testRunDumpTexInfo(self):
        cmdspec = [
                "python",
                str(self.scriptpath),
                "-log", LOG_LEVEL,
                "-materials_path", str(self.materials_path),
                "-d", "15",
                str(self.bsppath)
        ]
        result = subprocess.run(cmdspec, capture_output=CAPTURE_OUTPUT)
        self.assertEqual(result.returncode, 0)

    # @unittest.skip
    @unittest.skipIf(not ALLTESTS & 2, "skip flag")
    def testRunTexRemap(self):
        copy2(self.custommatpath_origin, self.custommatpath)
        cmdspec = [
                "python",
                str(self.scriptpath),
                "-log", LOG_LEVEL,
                "-materials_path", str(self.materials_path),
                str(self.bsppath)
        ]
        result = subprocess.run(cmdspec, capture_output=CAPTURE_OUTPUT)
        self.assertEqual(result.returncode, 0)
        
        # check that texture groups are preserved
        self.subTestTexgroup()

    # @unittest.skip
    @unittest.skipIf(not ALLTESTS & 4, "skip flag")
    def testRunTexRemapOtherFile(self):
        copy2(self.custommatpath_origin, self.custommatpath)
        cmdspec = [
                "python",
                str(self.scriptpath),
                "-log", LOG_LEVEL,
                "-materials_path", str(self.materials_path),
                "-o", str(self.bsppath_other),
                str(self.bsppath)
        ]
        result = subprocess.run(cmdspec, capture_output=CAPTURE_OUTPUT)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self.bsppath_other.exists())
        
        # check that texture groups are preserved
        self.subTestTexgroup(self.bsppath_other)        

    # @unittest.skip
    @unittest.skipIf(not ALLTESTS & 8, "skip flag")
    def testRunTexRemapEntity(self):
        # part 1: inject extra entities into bsp
        entdata = self.entpath.read_bytes()
        extras = EntityList.decode(entdata)
        with open(self.bsppath, "r+b") as f:
            bsp = BspFile(f)
            bsp.entities.data += extras.data
            bsp.dump(f)

        # part 2: run app
        cmdspec = [
                "python",
                str(self.scriptpath),
                "-log", LOG_LEVEL,
                # "-materials_path", str(self.materials_path),
                "-o", str(self.bsppath_other),
                str(self.bsppath)
        ]
        result = subprocess.run(cmdspec, capture_output=CAPTURE_OUTPUT)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self.bsppath_other.exists())        
        
        # part 3: check that texture groups are preserved
        self.subTestTexgroup(self.bsppath_other)

if __name__=="__main__":
    unittest.main()
