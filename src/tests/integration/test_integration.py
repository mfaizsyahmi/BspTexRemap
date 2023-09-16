''' I'm too lazy to write unit tests
'''
import unittest, subprocess, sys
from pathlib import Path
from shutil import copy2
# inject sys.path to be able to load jankbsp
sys.path.append(str(Path(__file__).parents[2]))
from jankbsp import BspFileBasic as BspFile
from jankbsp.types import EntityList

class TestApp(unittest.TestCase):
    def setUp(self):
        # if true, redirect output away from terminal
        self.CAPTURE_OUTPUT = True
        self.LOG_LEVEL = "info"
        
        # path to script file
        self.scriptpath = Path(__file__).parents[2] / "BspTexRemap.py"
        # path to fixtures path
        self.fixturepath = Path(__file__).parent / "fixtures"
        
        self.bsppath = self.fixturepath / "dm_hellhole.bsp"
        self.bsppath_origin = self.bsppath.with_suffix(".ORIGIN") # MUST EXIST
        self.bsppath_other = self.fixturepath / "output.bsp"
        
        self.texinfopath = self.fixturepath / "dm_hellhole_texinfo.txt"
        
        self.custommatpath = self.fixturepath / "dm_hellhole_custommat.txt"
        self.custommatpath_origin = self.custommatpath.with_suffix(".NOPE") # MUST EXIST
        
        self.entpath = self.fixturepath / "extras.ent" # MUST EXIST
        
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
    
    # @unittest.skip
    def testRunDumpTexInfo(self):
        cmdspec = [
                "python",
                str(self.scriptpath),
                "-log", self.LOG_LEVEL,
                "-materials_path", str(self.materials_path),
                "-d", "15",
                str(self.bsppath)
        ]
        result = subprocess.run(cmdspec, capture_output=self.CAPTURE_OUTPUT)
        self.assertEqual(result.returncode, 0)
    
    # @unittest.skip
    def testRunTexRemap(self):
        copy2(self.custommatpath_origin, self.custommatpath)
        cmdspec = [
                "python",
                str(self.scriptpath),
                "-log", self.LOG_LEVEL,
                "-materials_path", str(self.materials_path),
                str(self.bsppath)
        ]
        result = subprocess.run(cmdspec, capture_output=self.CAPTURE_OUTPUT)
        self.assertEqual(result.returncode, 0)
        
    # @unittest.skip
    def testRunTexRemapOtherFile(self):
        copy2(self.custommatpath_origin, self.custommatpath)
        cmdspec = [
                "python",
                str(self.scriptpath),
                "-log", self.LOG_LEVEL,
                "-materials_path", str(self.materials_path),
                "-o", str(self.bsppath_other),
                str(self.bsppath)
        ]
        result = subprocess.run(cmdspec, capture_output=self.CAPTURE_OUTPUT)
        self.assertEqual(result.returncode, 0)

    # @unittest.skip
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
                "-log", self.LOG_LEVEL,
                # "-materials_path", str(self.materials_path),
                "-o", str(self.bsppath_other),
                str(self.bsppath)
        ]
        result = subprocess.run(cmdspec, capture_output=self.CAPTURE_OUTPUT)
        self.assertEqual(result.returncode, 0)

if __name__=="__main__":
    unittest.main()
