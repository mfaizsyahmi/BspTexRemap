from hashlib import md5 # to check if lump has changed
from io import BytesIO # temp place to dump
from jankbsp.types import *

class BspLump:
    ''' most basic lump implementation that just loads/dumps raw data as is. '''
    
    def __init__(self, parent):
        # each lump must be initialized with the reference to its parent BspFile
        self._parent = parent # the parent BspFile

    def load(self, fp, length):
        self._length = length
        self._raw = fp.read(length)
        return self

    def dump(self, fp):
        return fp.write(self._raw)

    def _hash(self, raw=False, target=None, dumpargs=(),dumpkwargs={}):
        # calculates md5 hash from the raw or the dump
        h = md5()
        if raw: target=self._raw
        if target is not None:
            h.update(target)
            return h.digest()
        with BytesIO() as f:
            self.dump(f, *dumpargs, **dumpkwargs)
            h.update(f.getbuffer())
            return h.digest()

    @property
    def changed(self):
        return self._hash() != self._hash(raw=True)


class BspDataLump(BspLump):
    ''' extended BspLump for lumps that hold an array of objects, no headers
        DATATYPE must have "STRUCT" Struct property and "encode"/"decode" method
        if DATATYPE is generic type, class must have STRUCT for a single type
    '''
    DATATYPE = Vector # example

    def load(self, fp, length):
        cls = self.__class__
        data_struct = cls.STRUCT if hasattr(cls,"STRUCT") else cls.DATATYPE.STRUCT
        
        # make sure length is exact multiples of struct size
        assert not length % data_struct.size

        self = super().load(fp, length)

        size = data_struct.size
        if hasattr(cls,"STRUCT"):
            self.entries = [item[0] for item in cls.STRUCT.iter_unpack(self._raw)]
        elif hasattr(cls.DATATYPE, "decode"):
            self.entries = [
                cls.DATATYPE.decode(self._raw[offset:offset+size]) \
                for offset in range(0,length,size)
            ]

        return self

    def dump(self, fp):
        cls = self.__class__
        if hasattr(cls,"STRUCT"):
            print(cls,"packing using struct")
            return fp.write(b"".join([cls.STRUCT.pack(item) for item in self.entries]))
        elif hasattr(cls.DATATYPE, "encode"):
            print(cls,"packing using encode method of", cls.DATATYPE)
            return fp.write(b"".join([item.encode() for item in self.entries]))

