''' buildfuncs.py
    Copyright (c) 2023 M Faiz Syahmi @ kimilil
    Released under MIT License

    special functions for creating dpg items
'''
import dearpygui.dearpygui as dpg
import webbrowser
from pathlib import Path # so far used only for typing


## INTERNAL CONSTANTS
ASSETS_BASE_PATH = None
DPG_TEXTURE_REGISTRY = None
LINK_HANDLER_REGISTRY = None

## Helper functions ------------------------------------------------------------

def get_base_path():
    ''' INTERNAL
        returns a usable base path to load images from
    '''
    global ASSETS_BASE_PATH
    return ASSETS_BASE_PATH or Path.cwd()


def get_texture_registry():
    ''' INTERNAL
        returns a usable texture registry to load images to
    '''
    global DPG_TEXTURE_REGISTRY
    if DPG_TEXTURE_REGISTRY is None:
        DPG_TEXTURE_REGISTRY = dpg.add_texture_registry()
    return DPG_TEXTURE_REGISTRY


def get_link_handler_registry():
    ''' INTERNAL
        returns a configured link handler registry, which binds bound items' click
        event to open the stored url on user's browser
    '''
    global LINK_HANDLER_REGISTRY
    
    # d = click_data = (which_button, item id)
    cb = lambda _, d: webbrowser.get().open(dpg.get_item_user_data(d[1]))
    
    if LINK_HANDLER_REGISTRY is None:
        with dpg.item_handler_registry() as link_handler:
            dpg.add_item_clicked_handler(dpg.mvMouseButton_Left,callback=cb)
        LINK_HANDLER_REGISTRY = link_handler
        
    return LINK_HANDLER_REGISTRY


## Builder functions -----------------------------------------------------------

def add_url_text(content, **kwargs):
    ''' special dpg constructor for text links. it does the following:
        1. takes the custom kwarg "target" containing the target URL,
        2. removes it from the dpg.add_text creation (since it's not recognized)
        3. assigns target URL to the item's user_data property
        4. binds the created item to a handler registry, which responds to
           left-click by opening user's web browser to the URL stored in user_data
    '''
    url = None
    for prop in ("target", "url"):
        if prop in kwargs:
            url = kwargs[prop]
            del kwargs[prop]
    if not url:
        url = content.strip()

    # puts the url in user_data. This WILL OVERRIDE existing items
    kwargs["user_data"] = url
    
    self = dpg.add_text(content, **kwargs)
    dpg.bind_item_handler_registry(self, get_link_handler_registry())

    return self


def add_image(content, **kwargs):
    ''' special dpg constructor for image. associated prop name for the image
        path is "path" or "src". if neither exists, use the content i.e. the
        first item in the children bracket, which must be a text.
    '''
    imgpath = None
    for prop in ("path", "src"):
        if prop in kwargs:
            imgpath = Path(kwargs[prop])
            del kwargs[prop]
    if not imgpath:
        imgpath = Path(content)

    if not imgpath: return
    elif not imgpath.is_absolute():
        imgpath = get_base_path() / imgpath
    if not imgpath.exists(): return

    width, height, channels, data = dpg.load_image(str(imgpath))
    img = dpg.add_static_texture(
            width=width,
            height=height,
            default_value=data,
            parent=get_texture_registry()
    )

    self = dpg.add_image(img, **kwargs)

    return self
