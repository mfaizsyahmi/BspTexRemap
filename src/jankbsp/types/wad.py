from dataclasses import dataclass, field, astuple
from struct import Struct
from .miptex import MipTex

MAXTEXTURENAME = 16

# define exceptions
class BadWadFile(Exception):
    pass

@dataclass
class WadHeader:
    magic: bytes = b"WAD3"
    entries: int = 0
    dir_offset: int = 0
    
    STRUCT = Struct("<4sii")
    MAGICVAL = b"WAD3"
    HEADER_OFFSET = 0
    
    @classmethod
    def decode(cls, rawbytes):
        unpacked = cls.STRUCT.unpack(rawbytes)
        if unpacked[0] != cls.MAGICVAL:
            raise BadWadFile(" ".join(
                "Unrecognized file type",
                f"(signature '{str(unpacked[0])}' instead of '{str(cls.MAGICVAL)}')"
            ))
        return cls(*unpacked)
        
    def encode(self):
        return this.STRUCT.pack(*astuple(self))
        
    def astuple(self):
        return astuple(self)        
        
    @classmethod
    def load(cls, fp):
        return cls.decode(fp.read(cls.STRUCT.size))
    def dump(self, fp):
        return fp.write(self.encode()) # returns number of bytes written

@dataclass
class WadDirEntry:
    offset: int       = field(default=0)
    sizeondisk: int   = field(default=0)
    size: int         = field(default=0)
    type: int         = field(default=0) # byte
    compression: bool = field(default=0) # bool takes up 1 byte
    name: str         = field(default="")
    STRUCT = Struct(f"<iiib?xx{MAXTEXTURENAME}s")
    CP = "cp1252"

    @classmethod
    def decode(cls, rawbytes):
        unpacked = cls.STRUCT.unpack(rawbytes)
        name = unpacked[-1].partition(b"\x00")[0].decode(cls.CP)
        return cls(*unpacked[0:-1],name)
    def encode(self):
        parts = astuple(self)
        return self.__class__.STRUCT.pack(
                *parts[0:-1],
                parts[-1].encode(self.__class__.CP)
        )
    def astuple(self):
        return astuple(self)
    
    # load and dump methods provided for easier io
    @classmethod
    def load(cls, fp):
        return cls.decode(fp.read(cls.STRUCT.size))
    def dump(self, fp):
        return fp.write(self.encode()) # returns number of bytes written

@dataclass
class WadMipTex(MipTex):
    ''' Same as the BSP's version with these differences:
        - you can't unembed from it
        - direct dump/load methods for easier io
    '''
    def unembed(self):
        raise NotImplementedError("Cannot unembed WAD textures")
    
    # load and dump methods provided for easier io
    @classmethod
    def load(cls, fp, length):
        return cls.decode(fp.read(length))
    def dump(self, fp) -> int:
        return fp.write(self.encode()) # returns number of bytes written
