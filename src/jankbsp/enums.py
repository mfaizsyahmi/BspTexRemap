from enum import Enum, IntEnum, auto, unique

@unique
class Lumps(IntEnum):
    Entities     = auto()
    Planes       = auto()
    Textures     = auto()
    Vertices     = auto()
    Visibility   = auto()
    Nodes        = auto()
    Texinfo      = auto()
    Faces        = auto()
    Lighting     = auto()
    Clipnodes    = auto()
    Leafs        = auto()
    Marksurfaces = auto()
    Edges        = auto()
    Surfedges    = auto()
    Models       = auto()
    
@unique
class BlueShiftLumps(IntEnum):
    Planes       = auto() # swapped places
    Entities     = auto() # with this
    Textures     = auto() 
    Vertices     = auto() 
    Visibility   = auto() 
    Nodes        = auto() 
    Texinfo      = auto() 
    Faces        = auto() 
    Lighting     = auto() 
    Clipnodes    = auto() 
    Leafs        = auto() 
    Marksurfaces = auto() 
    Edges        = auto() 
    Surfedges    = auto() 
    Models       = auto() 

@unique
class PlaneTypes(IntEnum):
    X = 0       # Plane is perpendicular to given axis
    Y = 1
    Z = 2
    ANYX = 3    # Non-axial plane is snapped to the nearest
    ANYY = 4
    ANYZ = 5

@unique
class Contents(IntEnum):
    Empty        = -1
    Solid        = -2
    Water        = -3
    Slime        = -4
    Lava         = -5
    Sky          = -6
    Origin       = -7
    Clip         = -8
    Current_0    = -9
    Current_90   = -10
    Current_180  = -11
    Current_270  = -12
    Current_Up   = -13
    Current_Down = -14
    Translucent  = -15
