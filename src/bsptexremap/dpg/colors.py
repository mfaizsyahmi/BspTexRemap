''' colors.py
    colors and theming
'''

import dearpygui.dearpygui as dpg
from ..enums import MaterialEnum
from collections import namedtuple

class Subscriptable:
    ''' support for class[item] '''
    def __class_getitem__(cls, item):
        ''' support for class[item] (prefered way)'''
        if item in cls.__dict__: return cls.__dict__[item] 
        return None


_c = namedtuple("ColorRegistry", ["color","bg","fg"])
class MaterialColors(Subscriptable):
    ''' it's too hard to get easily-copyable RGB picker so here I just go
        through the colour wheel
    '''
        # text on default      background         fg over bg
    C = _c((255,255,255,255), (255,255,255,255), (  0,  0,  0,255)) # Concrete
    M = _c((255,  0,  0,255), (255,  0,  0,255), (255,255,255,255)) # Metal
    D = _c((255,127,  0,255), (255,127,  0,255), (255,255,255,255)) # Dirt
    V = _c((255,255,  0,255), (255,255,  0,255), (255,255,255,255)) # Vents
    G = _c((127,255,  0,255), (127,255,  0,255), (255,255,255,255)) # Grate
    T = _c((  0,255,  0,255), (  0,255,  0,255), (255,255,255,255)) # Tile
    S = _c((  0,255,127,255), (  0,255,127,255), (255,255,255,255)) # Slosh
    W = _c((  0,255,255,255), (  0,255,255,255), (255,255,255,255)) # Wood
    P = _c((  0,127,255,255), (  0,127,255,255), (255,255,255,255)) # Computer
    Y = _c((127,127,255,255), (  0,  0,255,255), (255,255,255,255)) # Glass
    F = _c((127,  0,255,255), (127,  0,255,255), (255,255,255,255)) # Flesh
    N = _c((255,  0,255,255), (255,  0,255,255), (255,255,255,255)) # SnowCS
    O = _c((255,  0,255,255), (255,  0,255,255), (255,255,255,255)) # SnowOF
    E = _c((255,  0,127,255), (255,  0,127,255), (255,255,255,255)) # Carpet
    A = _c(( 76,152,  0,255), ( 76,152,  0,255), (255,255,255,255)) # Grass
    X = _c(( 76,152,  0,255), ( 76,152,  0,255), (255,255,255,255)) # GrassCZ
    R = _c((192,192,192,255), (192,192,192,255), (  0,  0,  0,255)) # Gravel
    unknown = \
        _c((170,170,170,255), (170,170,170,255), (  0,  0,  0,255)) # unknown

class AppColors(Subscriptable):
    #              text color         background         fg over bg
    # Texts        (?)                unused             unused
    Help      = _c((  0,200,  0,255), (100,100,100,255), (  0,255,  0,255))
    #               texview name      texview label bg    texview label fg
    Embedded  = _c((255,255,255,255), (128, 64,  0,255), (  0,  0,  0,255))
    External  = _c((150,150,150,255), (100,100,100,255), (255,255,255,255))
    #               unused            texview label bg    texview label fg
    ToEmbed   = _c((  0,  0,  0,255), (  0,200,  0,255), (255,255,255,255))
    ToUnembed = _c((  0,  0,  0,255), (200,  0,  0,255), (255,255,255,255))

    Selected  = _c((  0,170,255,255), (  0,170,255,255), (  0,170,255,255))

class AppThemes(Subscriptable):             # applies to:
    Embedded   = "theme:texlabel_embedded"  # texview src button
    External   = "theme:texlabel_external"  # texview src button
    ToEmbed    = "theme:texlabel_to_embed"  # texview src button
    ToUnembed  = "theme:texlabel_to_unembed"# texview src button
    Normal     = "theme:galleryitem_normal" # texview group
    Selected   = "theme:texview_selected"   # texview group
    Uneditable = "theme:texview_uneditable" # texview slider

    Material__ = "theme:texview_mat__"      # texview slider
    Material_C = "theme:texview_mat_C"      # texview slider
    Material_M = "theme:texview_mat_M"      # texview slider
    Material_D = "theme:texview_mat_D"      # texview slider
    Material_V = "theme:texview_mat_V"      # texview slider
    Material_G = "theme:texview_mat_G"      # texview slider
    Material_T = "theme:texview_mat_T"      # texview slider
    Material_S = "theme:texview_mat_S"      # texview slider
    Material_W = "theme:texview_mat_W"      # texview slider
    Material_P = "theme:texview_mat_P"      # texview slider
    Material_Y = "theme:texview_mat_Y"      # texview slider
    Material_F = "theme:texview_mat_F"      # texview slider
    Material_N = "theme:texview_mat_N"      # texview slider
    Material_O = "theme:texview_mat_O"      # texview slider
    Material_E = "theme:texview_mat_E"      # texview slider
    Material_A = "theme:texview_mat_A"      # texview slider
    Material_X = "theme:texview_mat_X"      # texview slider
    Material_R = "theme:texview_mat_R"      # texview slider
    Material_unknown = \
                 "theme:texview_mat_unknown"# texview slider

def add_themes():
    with dpg.theme(tag="theme:main_window"):
        with dpg.theme_component(dpg.mvWindowAppItem):
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding,4,2)

    with dpg.theme(tag="theme:layout_table"):
        with dpg.theme_component(0):
            #dpg.add_theme_color(dpg.mvThemeCol_TableHeaderBg ,(15,86,135,255))
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding,8,8)

    with dpg.theme(tag="theme:normal_table"):
        with dpg.theme_component(0): pass
            #dpg.add_theme_color(dpg.mvThemeCol_TableHeaderBg ,(48,48,51,255))

    #### TexView Themes ####
    ### Popup ###
    with dpg.theme(tag="theme:texview_popup"):
        with dpg.theme_component(0):
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding,0,0)

    ### Normal/Selected  ###
    with dpg.theme(tag=AppThemes.Normal):
        with dpg.theme_component(dpg.mvGroup):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (150,0,0,255))

    with dpg.theme(tag=AppThemes.Selected):
        with dpg.theme_component(0):
            dpg.add_theme_color(dpg.mvThemeCol_Border, AppColors.Selected.bg)
            dpg.add_theme_color(dpg.mvThemeCol_Text,   AppColors.Selected.color)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)

    ### Embedded/External  ###
    with dpg.theme(tag=AppThemes.Embedded):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, AppColors.Embedded.bg)
            dpg.add_theme_color(dpg.mvThemeCol_Text,   AppColors.Embedded.fg)

    with dpg.theme(tag=AppThemes.External):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, AppColors.External.bg)
            dpg.add_theme_color(dpg.mvThemeCol_Text,   AppColors.External.fg)

    with dpg.theme(tag=AppThemes.ToEmbed):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, AppColors.ToEmbed.bg)
            dpg.add_theme_color(dpg.mvThemeCol_Text,   AppColors.ToEmbed.fg)

    with dpg.theme(tag=AppThemes.ToUnembed):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, AppColors.ToUnembed.bg)
            dpg.add_theme_color(dpg.mvThemeCol_Text,   AppColors.ToUnembed.fg)

    with dpg.theme(tag=AppThemes.Uneditable):
        with dpg.theme_component(dpg.mvSliderInt, enabled_state=False): # slider only
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg,         ( 29, 29, 31,255))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered,  ( 29, 29, 31,255))
            #dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered,  ( 21, 21, 22,255))
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab,      ( 37, 37, 38,255))
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive,( 24, 24, 24,255))
            dpg.add_theme_color(dpg.mvThemeCol_Text,            (151,151,151,255))
            #dpg.add_theme_color(dpg.mvThemeCol_Text,            (255,0,255,255))

    with dpg.theme(tag=AppThemes.Material__):
        with dpg.theme_component(dpg.mvSliderInt): # slider only
            pass

    for mat in MaterialEnum:
        tag = AppThemes[f"Material_{mat.value}"] or AppThemes.Material_unknown
        mat_color_entry = MaterialColors[mat.value] or MaterialColors.unknown
        with dpg.theme(tag=tag):
            with dpg.theme_component(dpg.mvSliderInt): # slider only
                dpg.add_theme_color(dpg.mvThemeCol_SliderGrab,
                                    mat_color_entry.bg)
                dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive,
                                    mat_color_entry.bg)
                dpg.add_theme_color(dpg.mvThemeCol_Text,
                                    mat_color_entry.color)


