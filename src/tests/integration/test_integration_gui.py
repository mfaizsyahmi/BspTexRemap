''' I'm too lazy to write unit tests
'''
import unittest, subprocess, sys
from pathlib import Path
from shutil import copy2
# inject sys.path to be able to load jankbsp
sys.path.append(str(Path(__file__).parents[2]))
from BspTexRemap_GUI import main as gui_main
from bsptexremap.dpg.modelcontroller import App
import dearpygui.dearpygui as dpg

ALLTESTS = 0b11111111 # bitflags for tests to run
CAPTURE_OUTPUT = False # if true, redirect output away from terminal
LOG_LEVEL = "info"    # log level for app

def run_after_gui_loaded(func):
    def wrap(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
        except:
            result = None
        return result
    return wrap

class TestApp(unittest.TestCase):
    def setUp(self):
        # path to where GUI script file and toml cfg file is
        self.basepath = Path(__file__).parents[1]
        
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
        
        # loads the app
        self.app = gui_main(self.basepath, False)
        # start rendering a few frames
        for _ in range(5):
            dpg.render_dearpygui_frame()

    def tearDown(self):
        dpg.destroy_context()
        for deleteme in [
                self.bsppath,
                self.texinfopath,
                self.custommatpath,
                self.bsppath_other
        ]:
            try: deleteme.unlink()
            except FileNotFoundError: pass

    def testOpenBsp(self):
        self.app.do.open_bsp_file(self.bsppath, True)
        
    def testReload(self):
        self.testOpenBsp()
        self.app.do.reload()
    
    def testClose(self):
        self.testOpenBsp()
        self.app.do.close()
    
    
if __name__=="__main__":
    unittest.main()
