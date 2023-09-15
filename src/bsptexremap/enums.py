from enum import IntEnum, StrEnum, IntFlag

# for materials.py
class MaterialEnum(StrEnum):
    Concrete = 'C'
    Metal    = 'M'
    Dirt     = 'D'
    Vents    = 'V'
    Grate    = 'G'
    Tile     = 'T'
    Slosh    = 'S'
    Wood     = 'W'
    Computer = 'P'
    Glass    = 'Y'
    Flesh    = 'F'
    Snow     = 'N'
    Carpet   = 'E' # new in CZDS
    Grass    = 'A' # new in CZDS
    GrassCZ  = 'X' # new in CZ
    Gravel   = 'R' # new in CZDS
    Default  = 'C'

class DumpTexInfoParts(IntFlag):
    Embedded        = 1
    External        = 2
    All             = 3
    Grouped         = 4
    Uniquegrouped   = 8
    # Header          = 1024