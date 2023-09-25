import dearpygui.dearpygui as dpg
from collections import namedtuple

class Subscriptable:
    def __getitem__(self, item): 
        ''' support for instance[mattype] '''
        return getattr(self, item)    

_c = namedtuple("ColorRegistry", ["color","bg","fg"])
class MaterialColors(Subscriptable):
        # text on default      background         fg over bg
    C = _c((199,199,199,255), (100,100,100,255), (255,255,255,255)) # Concrete 
    M = _c((153,167,173,255), (100,100,100,255), (255,255,255,255)) # Metal    
    D = _c((144, 85,128,255), (100,100,100,255), (255,255,255,255)) # Dirt     
    V = _c((133,125,255,255), (100,100,100,255), (255,255,255,255)) # Vents    
    G = _c((255,255,255,255), (100,100,100,255), (255,255,255,255)) # Grate    
    T = _c((255,255,255,255), (100,100,100,255), (255,255,255,255)) # Tile     
    S = _c((255,255,255,255), (100,100,100,255), (255,255,255,255)) # Slosh    
    W = _c((255,255,255,255), (100,100,100,255), (255,255,255,255)) # Wood     
    P = _c((255,255,255,255), (100,100,100,255), (255,255,255,255)) # Computer 
    Y = _c((255,255,255,255), (100,100,100,255), (255,255,255,255)) # Glass    
    F = _c((255,255,255,255), (100,100,100,255), (255,255,255,255)) # Flesh    
    N = _c((255,255,255,255), (100,100,100,255), (255,255,255,255)) # Snow     
    E = _c((255,255,255,255), (100,100,100,255), (255,255,255,255)) # Carpet   
    A = _c((255,255,255,255), (100,100,100,255), (255,255,255,255)) # Grass    
    X = _c((255,255,255,255), (100,100,100,255), (255,255,255,255)) # GrassCZ  
    R = _c((255,255,255,255), (100,100,100,255), (255,255,255,255)) # Gravel 
    
class AppColors(Subscriptable):
    #              (?)                unused             unused
    Help     = _c((  0,255,  0,255), (100,100,100,255), (  0,255,  0,255))
    #              texview name      texview label bg    texview label fg
    Embedded = _c((255,255,255,255), (128, 64,  0,255), (  0,  0,  0,255))
    External = _c((150,150,150,255), (100,100,100,255), (255,255,255,255))


class AppThemes:
    Embedded = "theme:texlabel_embedded"
    External = "theme:texlabel_external"

def add_themes():
    with dpg.theme(tag="theme:main_window"):
        with dpg.theme_component(dpg.mvWindowAppItem):
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding ,4,2)
            
    with dpg.theme(tag="theme:layout_table"):
        with dpg.theme_component(0):
            #dpg.add_theme_color(dpg.mvThemeCol_TableHeaderBg ,(15,86,135,255))
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding ,8,8)
            
    with dpg.theme(tag="theme:normal_table"):
        with dpg.theme_component(0): pass
            #dpg.add_theme_color(dpg.mvThemeCol_TableHeaderBg ,(48,48,51,255))
            
    with dpg.theme(tag="theme:galleryitem_normal"):
        with dpg.theme_component(dpg.mvGroup):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg ,(150,0,0,255))
    
    with dpg.theme(tag=AppThemes.Embedded):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button ,AppColors.Embedded.bg)
            dpg.add_theme_color(dpg.mvThemeCol_Text ,  AppColors.Embedded.fg)
            
    with dpg.theme(tag=AppThemes.External):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button ,AppColors.External.bg)
            dpg.add_theme_color(dpg.mvThemeCol_Text ,  AppColors.External.fg)

