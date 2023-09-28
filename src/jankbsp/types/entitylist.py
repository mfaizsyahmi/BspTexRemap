import re
from typing import *
from collections import UserList, UserDict
# from .multidict import MultiDict

class EntityList(UserList):
    ''' list class extended to add encode/decode for the entity lump '''
    CP = "cp1252"
    RE = re.compile(r"\"(?P<key>[^\"]*)\"\s+\"(?P<value>[^\"]*)\"")
    dict_factory = UserDict

    @classmethod
    def decode(cls, bytes):
        self = cls()

        current_obj = None
        for i, line in enumerate(bytes.decode(EntityList.CP).splitlines()):
            line_re = EntityList.RE.match(line)
            if line == "{":
                if current_obj:
                    self.append(current_obj)
                current_obj = cls.dict_factory()
            elif line == "}":
                self.append(current_obj)
                current_obj = None

            elif line_re is not None: # and current_obj:
                # current_obj.append(*line_re.groups())
                current_obj[line_re.group(1)] = line_re.group(2)
            elif not line_re:
                continue
            else:
                raise ValueError("Error parsing entity data")

        if current_obj:
            self.append(current_obj)
        return self

    def encode(self):
        lines = []
        for ent in self.data:
            lines.append("{")
            for k,v in ent.items():
                lines.append(f"\"{k}\" \"{v}\"")
            lines.append("}")
        return "\n".join(lines).encode(EntityList.CP) + b"\n\x00"
        # ending above inserts a newline-null termination pair
        # since compiler outputs always adds newline at the end

    def query_select(self, query:str):
        ''' my take on HTML DOM's querySelectorAll '''
        qsa_re = re.compile(r"""(?gmix)
(?:\s|^)                 # new class group start with whitespace or start of line
(?P<exclude>-)?          # exclude this class group
(?P<class>\w+\*?|\*)     # classname, can have a wildcard* at the end
(?:\#(?P<id>\w+))?       # targetname, no spaces
(?:\|(?P<flags>[\d+]+))? # flags, also flag1+flag2+...
|(?:(?<=\S)              # selector must not come after whitespace
 \:(?P<selector>\w+)     # name of :selector()
  \((?P<selector_data>[^)]*)\)) # selector data
|(?:(?<=\S)              # prop must not come after whitespace
  \[(?P<prop>[\w#]+)     # name of prop
    (?:(?P<op>[~^$*]?=|\|) # operator
    (?:(?P<q>['"])(?P<strval>.*)\9 # "string value"
      |(?P<val>[\w]*)              # word value
    ))?\])
        """)
        
        # primary filters
        f_c = lambda ent,val: ent["classname"].startswith(val.partition("*")[0])
        f_i = lambda ent,val: ent["targetname"] == val
        f_f = lambda ent,val: int(ent["spawnflags"]) & sum([int(x) for x in val.split("+")])
        
        # property ops
        f_p_ops = {
            "=" :  lambda prop,val: prop == val,
            "^=" : lambda prop,val: prop.startswith(val),
            "$=" : lambda prop,val: prop.endswith(val),
            "*=" : lambda prop,val: val in prop,
            "|" :  lambda prop,val: prop & val,
        }
        
        def _inbounds(ent,mins,maxs):
            o = [float(a) for a in ent["origin"].split(" ")]
            i = [float(a) for a in mins.split(" ")]
            j = [float(a) for a in maxs.split(" ")]
            return i[0] <= o[0] <= j[0] \
               and i[1] <= o[1] <= j[1] \
               and i[2] <= o[2] <= j[2]
        def _facing(ent,angle,spread):
            o = [float(a) for a in ent["angles"].split(" ")]
            i = [float(a) for a in angle.split(" ")]
            j = [float(a) for a in spread.split(" ")] if spread else [90,0]
            return i[0]-j[0] <= o[0] <= i[0]+j[0] \
               and i[1]-j[1] <= o[1] <= i[1]+j[1]
        f_s = {
            "point" : lambda ent,_ : "origin" in ent,
            "solid" : lambda ent,_ : "model" in ent \
                                     and re.match("\*\d+",ent["model"]),
            "inbounds": lambda ent, val: _inbounds(ent,val.split(",")),
            "facing":   lambda ent, val: _facing(ent,val.split(",")),
        }
        
        things = []
        current = None        
        for m in qsa_re.finditer(query):
            if "class" in m.groupdict:
                if current: things.append(current)
                current = m.groupdict
            elif "selector" in m.groupdict:
                current.setdefault("selectors",[]).append(m.groupdict)
            elif "prop" in m.groupdict:
                current.setdefault("props",[]).append(m.groupdict)
        things.append(current) # get the last item
        
        result_set = set()
        for thing in things:
            the_list = filter(lambda ent: f_c(ent,thing["class"]), self.data)
            if "id" in thing:
                the_list = filter(lambda ent: f_i(ent,thing["id"]), the_list)
            if "flags" in thing:
                the_list = filter(lambda ent: f_f(ent,thing["flags"]), the_list)
            for sel in thing["selectors"]:
                the_list = filter(lambda ent: \
                                  f_s[sel["selector"]]\
                                  (ent, sel["selector_data"]), the_list)
            for prop in thing["props"]:
                the_list = filter(lambda ent: prop["prop"] in ent, the_list)
                if "op" not in prop: continue
                the_list = filter(lambda ent: \
                                  f_p_ops[prop["op"]]\
                                  (ent[prop["prop"]], prop["strval"] or prop["val"]),
                                  the_list)
            this_result = set(the_list)
            
            if "exclude" in thing:
                result_set -= this_result
            else:
                result_set |= this_result
                
        return result_set
