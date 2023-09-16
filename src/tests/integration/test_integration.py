''' I'm too lazy to write unit tests
'''
import unittest
from pathlib import Path
from shutil import copy2
import subprocess

class TestApp(unittest.TestCase):
    def setUp(self):
        # if true, redirect output away from terminal
        self.CAPTURE_OUTPUT = False
        self.LOG_LEVEL = "info"
        
        # path to script file
        self.scriptpath = Path.cwd().parents[1] / "BspTexRemap.py"
        # path to fixtures path
        self.fixturepath = Path.cwd() / "fixtures"
        self.bsppath = self.fixturepath / "dm_hellhole.bsp"
        self.bsppath_origin = self.bsppath.with_suffix(".ORIGIN") # MUST EXIST
        self.texinfopath = self.fixturepath / "dm_hellhole_texinfo.txt"
        self.custommatpath = self.fixturepath / "dm_hellhole_custommat.txt"
        self.custommatpath_origin = self.custommatpath.with_suffix(".NOPE") # MUST EXIST
        self.materials_path = r"D:\SteamLibrary\steamapps\common\Half-Life\valve\sound\materials.txt"
        
        copy2(self.bsppath_origin, self.bsppath)
    
    def tearDown(self):
        for deleteme in [self.bsppath, self.texinfopath, self.custommatpath]:
            try: deleteme.unlink()
            except FileNotFoundError: pass
    
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

if __name__=="__main__":
    unittest.main()
