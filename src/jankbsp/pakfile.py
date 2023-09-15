''' 
PAK file library.
This implementation will try to emulate the classes and methods of ZipFile.

Notable differences:
    ZipInfo -> PakDirEntry
    
'''
from .types.pak import PakHeader, PakDirEntry, BadPakFile
from dataclasses import dataclass, field, astuple
from pathlib import Path, PurePath
from contextlib import AbstractContextManager

def is_pakfile(filename):
    with open(filename, "rb") as fp:
        data = fp.read(PakHeader.STRUCT.size)
        unpacked = PakHeader.STRUCT.unpack_from(data,0)
        return unpacked[0] == PakHeader.MAGICVAL

class PakFile(AbstractContextManager):
    def __init__(self, filename, mode="r"):
        self._file = filename
        self._mode = mode
        with open(filename, "rb") as fp:
            header = PakHeader.load(fp)
            
            fp.seek(header.dir_offset)
            size, count = PakHeader.STRUCT.size, header.entries
            dir_raw = fp.read(size * count) # read once
            self._entries = [\
                    PakDirEntry.decode(dir_raw[n*size:n*size+size]) \
                    for n in range(count)\
            ]
        return self
    def __enter__(self, *args, **kwargs):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
    
    