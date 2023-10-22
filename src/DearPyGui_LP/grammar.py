''' grammar.py
    Copyright (c) 2023 M Faiz Syahmi @ kimilil
    Released under MIT License

    Contains the grammar class for DPG_LP.
'''
from pyleri import (Grammar,
                    Keyword,
                    Regex,
                    Choice,
                    Optional,
                    Repeat,
                    Sequence,
                    List,
                    Ref,
                    Tokens)
from .mappings import DPG_NODE_KW_MAP, BINDINGS


class DpgLayoutGrammar(Grammar):
    ''' describes the layout grammar for DPG_LP
        root must have one s_elem, which represents a single dpg item:
            GROUP(horizontal) [ IMG ["hand.png"] "Hello!" ] /* a comment */
        where:
            GROUP        = element name
            (horizontal) = contains comma-separated properties associated with
                           the element. can be in the form of:
                           key=value (sets value of key)
                           flag (set attribute flag to True)
                           !flag (set attribute flag to False)
                           almost always corresponds to the kwargs dpg accepts in add_*

                           the parenthesis can be omitted.

            [...]        = contains the children (for containers) or content
                           (non-containers).

                           children can be other s_elem sequence (e.g. other elements)
                           or a simple "quoted text" which will be rendered as text.
                           text can span multiple lines; they are stripped before rendering.

                           depending on the element, either the first or all items
                           will be included. NOTE that the items in this bracket
                           IS NOT COMMA SEPARATED.

                           the square brackets CANNOT be omitted.

            /*...*/      = comment. can span multiple lines.

        for a list of supported element name and the dpg element it corresponds to,
        consult
    '''
    r_comment  = Regex   (r'(?s)/\*.*?\*/') # /*...*/
    
    t_prefix   = Tokens  ("+ - =")
    c_elname   = Sequence(
                    Optional(t_prefix),
                    Choice  (*(Keyword(kw) for kw in DPG_NODE_KW_MAP \
                               if kw[0] not in "+-="))
                 )

    r_str      = Regex   (r'(?s)(")(?:(?=(\\?))\2.)*?\1')
    r_num      = Regex   (r'-?[0-9]+(?:\.[0-9]+)?')
    c_alnum    = Choice  (r_str,r_num)

    t_negate   = Tokens  ('!')
    r_key      = Regex   (r'(?i)[a-z_][a-z0-9_]*')
    cs_listval = Choice  (
                    Sequence("[", List(c_alnum), "]"),
                    Sequence("(", List(c_alnum), ")")
                 )
    c_value    = Choice  (c_alnum,cs_listval)
    cs_kv      = Choice  (
                    Sequence(t_negate, r_key),
                    Sequence(r_key),
                    Sequence(r_key, "=", c_value)
                 )
    s_kvlist   = Optional(Sequence("(", List(cs_kv), ")"))

    c_binding  = Choice  (*(Keyword(kw, ign_case=True) for kw in BINDINGS))
    s_bindings = Repeat  (Sequence(":", c_binding, "(", c_alnum, ")"))

    s_elem     = Ref()
    c_children = Repeat  (Choice(s_elem, c_value, r_comment))
    s_elem     = Sequence(c_elname, s_kvlist, s_bindings, "[", c_children, "]")

    START      = Repeat(Choice(s_elem, r_comment))
