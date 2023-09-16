from dataclasses import dataclass, field, astuple, asdict
from collections import UserList # palette
from collections.abc import MutableSequence # palette
from struct import Struct
from typing import *
from ..enums import PlaneTypes

class StructData:
    ''' template data class that can be decoded/encoded from/to bytes
        use derived classes with @dataclasses only!
    '''
    STRUCT = Struct("<i") # sample
    @classmethod
    def decode(cls, rawbytes):
        return cls(*cls.STRUCT.unpack(rawbytes))
    def encode(self) -> bytearray:
        return self.__class__.STRUCT.pack(*astuple(self))
    def astuple(self):
        return astuple(self)

# class UnpackedData(UserList, StructData):
#     ''' lumps that hold unnamed unpacked data '''
#     pass

# basic data structs
@dataclass
class Vector(StructData):
    x: float
    y: float
    z: float
    STRUCT = Struct("<3f")

@dataclass
class Point(StructData):
    x: int
    y: int
    z: int
    STRUCT = Struct("<3i")

@dataclass
class Color(StructData):
    r: int
    g: int
    b: int
    STRUCT = Struct("3c")

class ColorArrayView(MutableSequence):
    ''' generic view object for binary array of colors. 
        this keeps the data in binary, reducing time and CPU usage.
        for use as palette or lightmap.
    '''
    def __init__(self, data):
        self.v = memoryview(data)
    def __getitem__(self, index): 
        return Color.decode(self.v[index*3:index*3+3])
    def __setitem__(self, index, val: tuple | Color): 
        self.v[index*3:index*3+3] = val.encode() if isinstance(val, Color) \
                else Color.STRUCT.pack(*val)
    def __delitem__(self, index): 
        return NotImplemented
    def __len__(self): 
        return len(self.v // 3)
    def insert(self, index, val): 
        return NotImplemented
    

class Palette(UserList):
    @classmethod
    def decode(cls, rawbytes):
        self = cls()
        for values in Color.STRUCT.iter_unpack(rawbytes):
            self.append(Color(*values))
        return self

    def encode(self):
        return b"".join([c.encode() for c in self.data])

# bsp data structs
# Note: all firstX/numX pairs have been renamed to X_index/X_count
# e.g. firstface -> face_index, numfaces -> face_count

@dataclass
class BoundingBox:
    min: Vector
    max: Vector
@dataclass
class ShortBoundingBox:
    min: Point
    max: Point

@dataclass
class BspModel(StructData):
    bbox: BoundingBox
    origin: Vector
    headnode: Tuple[int,int,int,int]
    visleafs: int
    face_index: int
    face_count: int
    STRUCT = Struct("<9f7i")
    @classmethod
    def decode(cls, rawbytes):
        unpacked = BspModel.STRUCT.unpack(rawbytes)
        return cls(
            BoundingBox( Vector(*unpacked[0:3]), Vector(*unpacked[3:6]) ), # bbox
            Vector(*unpacked[6:9]), # origin
            tuple(unpacked[9:13]), # headnode
            *unpacked[13:] # visleafs, face_index, face_count
        )
    def encode(self):
        parts = astuple(self)
        return BspModel.STRUCT.pack(
            *parts[0][0], *parts[0][1],
            *parts[1],
            *parts[2],
            *parts[3:]
        )

@dataclass
class BspPlane(StructData):
    normal: Vector
    distance: float
    type: PlaneTypes
    STRUCT = Struct("<4fi")
    @classmethod
    def decode(cls, rawbytes):
        unpacked = BspPlane.STRUCT.unpack(rawbytes)
        return cls(Vector(*unpacked[0:3]), *unpacked[3:])
    def encode(self):
        return BspPlane.STRUCT.pack(*self.normal.astuple(), self.distance, self.type)

@dataclass
class BspNode(StructData):
    plane_id: int
    children: Tuple[int,int] # front,back
    bbox: ShortBoundingBox
    face_index: int
    face_count: int
    STRUCT = Struct("<ihh6hHH")
    @classmethod
    def decode(cls, rawbytes):
        unpacked = BspNode.STRUCT.unpack(rawbytes)
        return cls(
            unpacked[0],
            tuple(unpacked[1:3]),
            ShortBoundingBox(Point(*unpacked[3:6]),Point(*unpacked[6:9])),
            *unpacked[9:]
        )
    def encode(self):
        parts = astuple(self)
        return BspNode.STRUCT.pack(
            parts[0],
            *parts[1],
            *parts[2][0], *parts[2][1],
            *parts[3:]
        )
@dataclass
class BspClipNode(StructData):
    plane_id: int
    children: Tuple[int,int] # front,back; negative is contents
    STRUCT = Struct("<Ihh")
    @classmethod
    def decode(cls, rawbytes):
        unpacked = BspClipNode.STRUCT.unpack(rawbytes)
        return cls( unpacked[0], tuple(unpacked[1:3]) )
    def encode(self):
        return BspClipNode.STRUCT.pack( self.plane_id, *self.children )

@dataclass
class BspTexInfo(StructData):
    s_vector: Vector
    s_shift: float
    t_vector: Vector
    t_shift: float
    miptex_id: int
    flags: int
    STRUCT = Struct("<8fII")
    @classmethod
    def decode(cls, rawbytes):
        unpacked = BspTexInfo.STRUCT.unpack(rawbytes)
        return cls(
            Vector(*unpacked[0:3]), unpacked[3],
            Vector(*unpacked[4:7]), unpacked[7],
            *unpacked[8:]
        )
    def encode(self):
        parts = astuple(self)
        return BspTexInfo.STRUCT.pack(
            *parts[0], parts[1],
            *parts[2], parts[3],
            *parts[4:]
        )

@dataclass
class BspFace(StructData):
    plane_id: int
    plane_side: int
    edge_index: int # first edge
    edge_count: int # edge count
    texinfo_id: int
    styles: Tuple[int,int,int,int]
    lightmap_offset: int
    STRUCT = Struct("<2HI2H4cI")
    @classmethod
    def decode(cls, rawbytes):
        unpacked = BspFace.STRUCT.unpack(rawbytes)
        return cls( *unpacked[0:5], tuple(unpacked[5:9]), unpacked[9] )
    def encode(self):
        parts = astuple(self)
        return BspFace.STRUCT.pack( *parts[0:5], *parts[5], parts[6] )

@dataclass
class BspEdge(StructData):
    index1: int
    index2: int
    STRUCT = Struct("<2H")
    def reversed(self):
        ''' surfedges pointing to a negative index is asking for edge where the 
            two indices were flipped
        '''
        return BspEdge(self.index2,self.index1)

@dataclass
class BspLeaf(StructData):
    contents: int
    visleaf: int # if -1, the whole map is visible from here
    bbox: ShortBoundingBox
    marksurface_index: int # first marksurface
    marksurface_count: int # length of marksurfaces
    ambient_levels: Tuple[int,int,int,int] # UNUSED
    STRUCT = Struct("<ii6h2H4c")
    @classmethod
    def decode(cls, rawbytes):
        unpacked = BspLeaf.STRUCT.unpack(rawbytes)
        return cls(
            *unpacked[0:2],
            ShortBoundingBox( Point(*unpacked[2:5]), Point(*unpacked[5:8]) ),
            *unpacked[8:10], tuple(unpacked[10:])
        )
    def encode(self):
        parts = astuple(self)
        return BspLeaf.STRUCT.pack( 
            *parts[0:2], 
            *parts[2][0], *parts[2][1], 
            *parts[3:5], *parts[5]
        )
