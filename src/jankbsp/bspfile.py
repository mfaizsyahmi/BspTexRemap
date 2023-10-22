from struct import Struct
from .enums import Lumps
from .types import *
from .lumps import *


class BspFile:
    HEADER_STRUCT = Struct(f"<i{len(Lumps)*2}i")
    MAGIC = 30
    LUMPCLASSES = {
        Lumps.Entities     : BspEntityLump,
        Lumps.Planes       : BspPlanesLump,
        Lumps.Textures     : BspTextureLump,
        Lumps.Vertices     : BspVerticesLump,
        Lumps.Visibility   : BspLump,
        Lumps.Nodes        : BspNodesLump,
        Lumps.Texinfo      : BspTexInfoLump,
        Lumps.Faces        : BspFacesLump,
        Lumps.Lighting     : BspLightmapLump,
        Lumps.Clipnodes    : BspClipnodesLump,
        Lumps.Leafs        : BspLeavesLump,
        Lumps.Marksurfaces : BspMarksurfacesLump,
        Lumps.Edges        : BspEdgesLump,
        Lumps.Surfedges    : BspSurfedgesLump,
        Lumps.Models       : BspModelsLump
    }
    dirty_texture_encode = True # uses the dirty texture lump encode

    def __init__(self, *args, **kwargs):
        if args or kwargs:
            self.load(*args, **kwargs)
            
    def load(self, fp, lump_enum=Lumps):
        ''' a custom lump_enum can be supplied for BSPs that don't use
            default lump enumeration (Blue Shift)
            
            (implementation note: use Lumps[lump_enum[x].name] to translate to 
            normal lumps)
        '''
        header = fp.read(BspFile.HEADER_STRUCT.size)
        unpacked = BspFile.HEADER_STRUCT.unpack_from(header)
        self.version = unpacked[0]
        assert self.version == BspFile.MAGIC

        # use the member of enum Lumps to access member of these dicts
        self.lumps = {}
        # dict of [enum] = offset. used to determine order of lumps
        lump_order_dict = {}
        for i, lump_member in enumerate(lump_enum):
            lump_member_translated = Lumps[lump_member.name]
            lump_offset = unpacked[2*i+1]
            lump_length = unpacked[2*i+2]
            lump_order_dict[lump_member_translated] = lump_offset

            fp.seek(lump_offset)
            if lump_member_translated in self.__class__.LUMPCLASSES:
                lump_cls = self.__class__.LUMPCLASSES[lump_member_translated]
            else:
                lump_cls = BspLump
                
            self.lumps[lump_member_translated] = lump_cls(self)
            self.lumps[lump_member_translated].load(fp,lump_length)

        self._lump_order = list(l for l in sorted(lump_order_dict.items(), \
                key=lambda item: item[1]))
        return self

    def dump(self, fp, lump_enum=Lumps):
        ''' a custom lump_enum can be supplied for BSPs that don't use
            default lump enumeration (Blue Shift)
            
            (implementation note: use Lumps[lump_enum[x].name] to translate to 
            normal lumps)
        '''    
        lump_dir = {}

        # write lump contents
        fp.seek(BspFile.HEADER_STRUCT.size)
        for lumpenum,_unused in self._lump_order:
            fp.seek((4-fp.tell()&3) % 4, 1) # this aligns to closest 4th bytes
            lump_offset = fp.tell()
            if lumpenum == Lumps.Textures:
                lump_length = self.lumps[lumpenum].dump(fp, self.dirty_texture_encode)
            else:
                lump_length = self.lumps[lumpenum].dump(fp) # return num bytes written
            lump_dir[lumpenum] = [lump_offset, lump_length]

        # write header and directory
        lump_dirlist = []
        for i, lump_member in enumerate(lump_enum):
            lump_dirlist += lump_dir[Lumps[lump_member.name]]

        header = BspFile.HEADER_STRUCT.pack(BspFile.MAGIC, *lump_dirlist)
        fp.seek(0)
        fp.write(header)
    
    def clone(self, fp):
        ''' returns a new instance of the bsp file by way of dumping to a buffer,
            then loading a new instance off that buffer 
        '''
        self.dump(fp)
        cloned = PakFile().load(fp)
        return cloned
    
    @property
    def entities(self): return self.lumps[Lumps.Entities].entries
    @property
    def planes(self): return self.lumps[Lumps.Planes].entries
    @property
    def textures(self): return self.lumps[Lumps.Textures].entries
    @property
    def textures_m(self): return self.lumps[Lumps.Textures].embedded_entries
    @property
    def textures_x(self): return self.lumps[Lumps.Textures].external_entries
    @property
    def vertices(self): return self.lumps[Lumps.Vertices].entries
    @property
    def visdata(self): return self.lumps[Lumps.Visibility]._raw
    @property
    def nodes(self): return self.lumps[Lumps.Nodes].entries
    @property
    def texinfo(self): return self.lumps[Lumps.Texinfo].entries
    @property
    def faces(self): return self.lumps[Lumps.Faces].entries
    @property
    def lightmap(self): return self.lumps[Lumps.Lighting].entries
    @property
    def clipnodes(self): return self.lumps[Lumps.Clipnodes].entries
    @property
    def leaves(self): return self.lumps[Lumps.Leafs].entries
    @property
    def marksurfaces(self): return self.lumps[Lumps.Marksurfaces].entries
    @property
    def edges(self): return self.lumps[Lumps.Edges].entries
    @property
    def surfedges(self): return self.lumps[Lumps.Surfedges].entries
    @property
    def models(self): return self.lumps[Lumps.Models].entries


class BspFileBasic(BspFile):
    ''' Subclass of BspFile with only entity and texture lumps editable '''
    LUMPCLASSES = {
        Lumps.Entities : BspEntityLump,
        Lumps.Textures : BspTextureLump
    }

    # all these properties aren't supported
    @property
    def planes(self): return None
    @property
    def vertices(self): return None
    @property
    def visdata(self): return None
    @property
    def nodes(self): return None
    @property
    def texinfo(self): return None
    @property
    def faces(self): return None
    @property
    def lightmap(self): return None
    @property
    def clipnodes(self): return None
    @property
    def leaves(self): return None
    @property
    def marksurfaces(self): return None
    @property
    def edges(self): return None
    @property
    def surfedges(self): return None
    @property
    def models(self): return None
