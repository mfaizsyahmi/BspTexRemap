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
