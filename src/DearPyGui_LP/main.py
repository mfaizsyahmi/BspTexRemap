''' main.py
    Copyright (c) 2023 M Faiz Syahmi @ kimilil
    Released under MIT License

    Contains the user-facing functions for DPG_LP.
'''
from . import mappings, treefuncs as tf, buildfuncs as bfn
from .grammar import DpgLayoutGrammar
from pathlib import Path # so far used only for typing
from logging import getLogger
log = getLogger(__name__)

# static instance
_dpg_grammar = DpgLayoutGrammar() 

###----------Setup Function----------###
def setup(asset_base_path : str|Path = None,
          texture_registry : str|int = None,
          link_color : tuple[int|float] | list[int|float] = None):
    ''' sets up the following (all optional):
        - base path for assets
        - dpg texture registry to load images to
        - link color
    '''
    bfn.ASSETS_BASE_PATH = asset_base_path
    bfn.DPG_TEXTURE_REGISTRY = texture_registry
    if type(link_color) in (list,tuple) and len(link_color) >= 3:
        mappings.DPG_NODE_KW_MAP["URL"].kwargs["color"] = link_color


###--------Grammar Functions---------###
def add_grammar_element(
        element_name:str,
        constructor:callable,
        def_kwargs:dict=None,
        child_content_slice:slice=None
):
    ''' allows addition of new elements to the grammar
    '''
    if def_kwargs is None: def_kwargs = {}
    mappings.DPG_NODE_KW_MAP[element_name] = mappings.DpgNodeMap(
        element_name.upper(),
        constructor,
        def_kwargs,
        child_content_slice
    )
    # reinstantiates the grammar object to load the new stuff
    _dpg_grammar = DpgLayoutGrammar() 

def add_grammar_elements(new_mapping:dict[str,mappings.DpgNodeMap]):
    ''' batch version of the above. use only if you know what you're doing.
    '''
    mappings.DPG_NODE_KW_MAP.update(new_mapping)
    # reinstantiates the grammar object to load the new stuff
    _dpg_grammar = DpgLayoutGrammar() 


###---------Layout Functions---------###
def parse_layout(layout_text:str):
    return _dpg_grammar.parse(layout_text)

def parse_layout_file(layout_file:str|Path):
    return parse_layout(Path(layout_file).read_text())
    
def layout_items(parse_result, parent=None):
    log.debug("Is parsed layout valid? %s", parse_result.is_valid)
    return tf.parse_dpg_elem(parse_result.tree.children[0], parent)

def layout_items_from_file(layout_file:str|Path, parent=None):
    return layout_items(parse_layout_file(layout_file), parent)


###--------Callback Functions--------###
def add_named_callback(name:str, callback:callable):
    ''' use this to set a name to a callback. then, you can use the name
        when defining an element's callback property.
    '''
    mappings.CALLBACKS[name] = callback
    
def add_named_callbacks(callback_map:dict[str,callable]):
    ''' batch version of the above. 
    '''
    mappings.CALLBACKS.update(callback_map)

