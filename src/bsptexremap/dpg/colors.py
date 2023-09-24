import dearpygui.dearpygui as dpg

class MaterialColors:
    C = (199,199,199) # Concrete 
    M = (153,167,173) # Metal    
    D = (144, 85,128) # Dirt     
    V = (133,125,255) # Vents    
    G = (255,255,255) # Grate    
    T = (255,255,255) # Tile     
    S = (255,255,255) # Slosh    
    W = (255,255,255) # Wood     
    P = (255,255,255) # Computer 
    Y = (255,255,255) # Glass    
    F = (255,255,255) # Flesh    
    N = (255,255,255) # Snow     
    E = (255,255,255) # Carpet   
    A = (255,255,255) # Grass    
    X = (255,255,255) # GrassCZ  
    R = (255,255,255) # Gravel   

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
