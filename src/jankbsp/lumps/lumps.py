from .base import BspLump, BspDataLump
from itertools import pairwise, accumulate # for texturelump
from math import ceil # vislump
from operator import itemgetter
from struct import Struct
from collections.abc import MutableSequence # for lightmap view
from jankbsp.types import *
from jankbsp.enums import Lumps

class BspEntityLump(BspLump):
    ''' entity lump
        extended to provide a MultiDict interface for the entity data
    '''
    def load(self, fp, length):
        super().load(fp, length)
        self.entries = EntityList.decode(self._raw)
        return self

    def dump(self, fp):
        return fp.write(self.entries.encode())


class BspPlanesLump(BspDataLump):
    ''' planes lump '''
    DATATYPE = BspPlane


class BspTextureLump(BspLump):
    ''' textures lump '''
    
    def load(self, fp, length):
        """ loads texture data
            this fn assumes that the texture entries are sequential and tightly packed
        """
        super().load(fp, length) # reads to self._raw. don't read fp after this!

        count = int.from_bytes(self._raw[0:4],byteorder='little')
        # entry offsets + the length at the end
        # this would be iterated pairwise to extract the raw bytes for each entry
        boundaries = [
                int.from_bytes( 
                        self._raw[ i*4+4 : i*4+8 ],
                        byteorder='little',
                        signed=True 
                ) for i in range(count)
        ] + [len(self._raw)]

        self.entries = []
        for start, end in pairwise(boundaries):
            self.entries.append(MipTex.decode(self._raw[start:end]))

        # calculate the hash of the dumped data as is, since it's impossible to
        # get the same hash as the raw data due to how texture names are stored
        # self._inithash = self._hash()

        return self

    def dump(self, fp, dirty_encode=False, raw_if_unchanged=False):
        ''' dump textures
            dirty_encode pastes the texture name over the garbage as read
        '''
        if raw_if_unchanged and not self.changed:
            return fp.write(self._raw)

        front_size = len(self.entries) * 4 + 4
        entry_data = [entry.encode(dirty_encode) for entry in self.entries]
        entry_offsets = [0] + list(accumulate([len(data) for data in entry_data]))
        entry_offsets = [x+front_size for x in entry_offsets[0:len(self.entries)] ]
        front_data = [len(entry_data).to_bytes(4,byteorder='little')] \
                + [x.to_bytes(4,byteorder='little',signed=True) for x in entry_offsets]

        return fp.write(b"".join(front_data + entry_data))

    @property
    def embedded_entries(self): # Read-only!
        return list(filter(lambda tex:not tex.is_external,self.entries))
    @property
    def external_entries(self): # Read-only!
        return list(filter(lambda tex:tex.is_external,self.entries))
    @property
    def changed(self):
        #return self._hash() != self._inithash
        # dump with dirty encode enabled. should give identical hash to _raw
        return self._hash(dumpargs=(True)) != self._hash(raw=True)


class BspVerticesLump(BspDataLump):
    ''' vertices lump '''
    DATATYPE = Vector

class BspVisLump(BspLump):
    ''' visibility lump 
        no unpacking the PVS on load since apparently the algo is fast enough
        (also because we don't know the leaf count)
    '''
    def unpack_pvs_bytes(self,start,len) -> bytes:
        ''' PVS unpack
            start is the byte offset
            len is the number of bits/leaves to unpack
        '''
        result = b"\x00" * ceil(len/8)
        v = start;
        l = 0
        while l < len:
            if self._raw[v]: # filled byte
                result[v-start] = self._raw[v]
                l += 8
                v += 1
            else: # empty byte, skip bytes
                # next byte represents number of zero bytes
                l += 8 * int.from_bytes(self._raw[v+1])
                v += 2 # skip the byte that counts zero bytes in data
        return result

class BspNodesLump(BspDataLump):
    ''' nodes lump '''
    DATATYPE = BspNode

class BspTexInfoLump(BspDataLump):
    ''' texinfo lump '''
    DATATYPE = BspTexInfo

class BspFacesLump(BspDataLump):
    ''' faces lump '''
    DATATYPE = BspFace

class BspLightmapLump(BspLump):
    ''' lightmap lump '''
    @property
    def entries(self): return ColorArrayView(self._raw)

class BspClipnodesLump(BspDataLump):
    ''' clipnodes lump '''
    DATATYPE = BspClipNode

class BspLeavesLump(BspDataLump):
    ''' leaves lump '''
    DATATYPE = BspLeaf
    
    def get_visible_leaves(self, leaf):
        ''' returns leaves visible from the given leaf '''
        if not len(self._parent.visdata): # no vis data
            return self.entries # everything is visible
        elif leaf.visleaf < 0:
            return self.entries # everything is visible from here
        # else
        result = []
        pvs_bytes = self._parent.lumps[Lumps.Visibility]\
            .unpack_pvs_bytes(leaf.visleaf, len(self.entries))
        for l in range(len(self.entries)):
            if pvs_bytes[l//8]&(l%8):
                result.append(self.entries[l])
        return result
    
    def get_faces(self, leaf):
        return itemgetter(
            *self._parent.marksurfaces[\
                leaf.marksurface_index:leaf.marksurface_index+leaf.marksurface_count\
            ]
        )(self._parent.faces)

class BspMarksurfacesLump(BspDataLump):
    ''' marksurfaces lump '''
    STRUCT = Struct("<H")

class BspEdgesLump(BspDataLump):
    ''' edges lump '''
    DATATYPE = BspEdge

class BspSurfedgesLump(BspDataLump):
    ''' surfedges lump '''
    STRUCT = Struct("<i")

class BspModelsLump(BspDataLump):
    ''' models lump '''
    DATATYPE = BspModel

