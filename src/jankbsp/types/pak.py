from dataclasses import dataclass, field, astuple
from struct import Struct
from .miptex import MipTex

MAXFILENAME = 56

# define exceptions
class BadPakFile(Exception):
    pass

@dataclass
class PakHeader:
    magic: bytes = b"PACK"
    entries: int = 0
    dir_offset: int = 0
    
    STRUCT = Struct("<4sii")
    MAGICVAL = b"PACK"
    HEADER_OFFSET = 0
    
    @classmethod
    def decode(cls, rawbytes):
        unpacked = cls.STRUCT.unpack(rawbytes)
        if unpacked[0] != cls.MAGICVAL:
            raise BadPakFile(" ".join(
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
class PakDirEntry:
    name: str   = field(default="")
    offset: int = field(default=0)
    size: int   = field(default=0)
    STRUCT = Struct(f"<{MAXFILENAME}sii")
    CP = "cp1252"

    @classmethod
    def decode(cls, rawbytes):
        unpacked = cls.STRUCT.unpack(rawbytes)
        name = unpacked[0].partition(b"\x00")[0].decode(cls.CP)
        return cls(name,*unpacked[1:])
    def encode(self):
        parts = astuple(self)
        return self.__class__.STRUCT.pack(
                parts[0].encode(self.__class__.CP),
                *parts[1:]
        )
    def astuple(self):
        return astuple(self)
    
    # load and dump methods provided for easier io
    @classmethod
    def load(cls, fp):
        return cls.decode(fp.read(cls.STRUCT.size))
    def dump(self, fp):
        return fp.write(self.encode()) # returns number of bytes written
