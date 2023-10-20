''' DearPyGui_LP aka DPG_LP
    Copyright (c) 2023 M Faiz Syahmi @ kimilil
    Released under MIT License

    the main entry point for import of DPG_LP
    -> exposes the front facing functions of main.py
'''
from .main import (
    setup,
    add_grammar_element,
    add_grammar_elements,
    parse_layout,
    parse_layout_file,
    layout_items,
    layout_items_from_file,
    add_named_callback,
    add_named_callbacks,
)
