from dataclasses import dataclass, field
from struct import Struct
from typing import *
from PIL import Image
from ..types import ColorArrayView, Color

class DimensionError(Exception):
    pass

@dataclass
class MipTex:
    name: str
    width: int
    height: int
    mip0: bytearray = field(default=None)
    mip1: bytearray = field(default=None)
    mip2: bytearray = field(default=None)
    mip3: bytearray = field(default=None)
    color_count: int = field(default=256)
    palette: bytearray = field(default=None)
    is_external: bool = field(init=False,default=False)
    # _rawname: bytearray = field(init=False, default_factory=bytearray(16))

    STRUCT = Struct("<16s6I")
    PALETTE_PAD = 2
    PALETTE_COLORS = 256
    PALETTE_SIZE = 768
    CP = "cp1252"
    
    @classmethod
    def decode(cls, rawbytes):
        unpacked = MipTex.STRUCT.unpack_from(rawbytes,0)
        # this _will_ contain junk after the string terminator, 
        # so must be partitioned. after that it must be encoded.
        name = unpacked[0].partition(b"\x00")[0].decode(MipTex.CP)
        
        self = cls(name, *unpacked[1:3])
        self._rawname = unpacked[0]

        if unpacked[3:] == (0,0,0,0):
            self.is_external = True
            return self

        for i in range(4):
            mip_pos = unpacked[3+i]
            mip_len = self.width * self.height // (4**i)
            setattr(self, f"mip{i}", bytearray(rawbytes[mip_pos:mip_pos+mip_len]))
            
            if i==3: # load palette at the end of mip3
                pal_pos = mip_pos + mip_len + 2
                self.color_count = int.from_bytes(
                        rawbytes[mip_pos+mip_len:pal_pos], 
                        byteorder='little'
                )
                self.palette = bytearray(rawbytes[pal_pos:pal_pos+MipTex.PALETTE_SIZE])

        return self

    def encode(self, dirty=False):
        ''' dirty mode stuffs the name back to the raw name struct, hoping it'd
            recreate the entire lump 1:1 with original if nothing is changed
        '''
        header_parts = [self.name.encode(MipTex.CP),self.width,self.height]\
                + [0,0,0,0]
        if dirty:
            rawname = bytearray(self._rawname)
            rawname[0:len(header_parts[0])+1] = header_parts[0] + b"\x00"
            header_parts[0] = rawname
        # truncate long names
        if len(header_parts[0]) > 15:
            header_parts[0] = header_parts[0][0:15] + b"\x00"
        
        body = b""
        if not self.is_external:
            mip_offs = MipTex.STRUCT.size
            for i in range(4):
                header_parts[3+i] = mip_offs + len(body)
                body += self.get_mip(i) # get_mip generates mips if it doesn't exist
            # add a short with the color count, then the color palette (fixed size)
            body += len(self.palette).to_bytes(2,byteorder='little') + self.palette
            
        return MipTex.STRUCT.pack(*header_parts) + body

    @property
    def size(self):
        ''' calculated size of the struct
            the total mip size is 1 + 1/4 + 1/16 + 1/64 times the size of the first
        '''
        return MipTex.STRUCT.size if self.is_external \
        else MipTex.STRUCT.size + MipTex.PALETTE_PAD + MipTex.PALETTE_SIZE \
                + int(len(self.mip0) * 1.328125)

    def unembed(self):
        ''' make MipTex entry external. no turning back! '''
        if not self.is_external:
            self.is_external = True
            self.mip0, self.mip1, self.mip2, self.mip3 = (None,None,None,None)
        return self

    @property
    def paletteview(self):
        return ColorArrayView(self.palette)

    def get_mip(self, level=0):
        """ returns existing mip, or generates them on the fly.
            this guarantees that mips are available to dump for new images
        """
        if self.mip0 is None:
            return None
        elif getattr(self,f"mip{level}") is not None:
            return getattr(self,f"mip{level}")
        # implicit else
        
        # prepare the byte array of the target mip level
        values = bytearray(self.width*self.height/4**level)
        pos = 0
        # sample the about center pixel of each 2^levelx2^level square
        for row in range(2*(level-1), self.height, 2**level):
            for col in range(2*(level-1), self.width, 2**level):
                values[pos] = self.mip0[row*self.width+col]
                pos += 1

        setattr(self, f"mip{level}", values)
        return values

    @classmethod
    def from_image(cls, img:Image, name):
        if img.width % 8 or img.height % 8:
            raise ValueError("image dimensions not divisible by 8")
        elif img.mode not in ["P", "L"]:
            raise ValueError("image not in indexed mode")

        this = cls(name[0:15], img.width, img.height)

        # save only the full size mip
        this.mip0 = b"".join(img.getdata())
        this.palette = b"".join(img.getpalette())
        return this
    
    def to_image(self):
        if self.mip0 is None: return None
        img = Image.new("P", (self.width,self.height))
        img.putpalette(self.palette)
        img.putdata(self.mip0)
        return img

    def fix_water(self, fog_color:Color|bytes|str=None,fog_intensity:int=None):
        ''' if water texture bitmap data points to index #3 or #4,
            re-quantize the image to vacate the bitmap from those indices
            (palette #3 and #4 defines fog colour/intensity so it ought to never
            be referenced in the bitmap)
        '''
        # skips:
        # -non-water texture
        # empty data
        # mip0 doesn't point to palette #3/4 (no problem)
        if self.name[0] != "!" \
        or not self.mip0 \
        or not b"\x03" in self.mip0 or not b"\x04" in self.mip0:
            return self
        
        # quantize and get new mip and palette
        new_img = self.to_image().quantize(
                colors=254, # 256 minus 2 fog indices
                method=Image.MAXCOVERAGE
        )
        mip = bytearray(new_img.getdata())
        pal = bytearray(new_img.getpalette())
        
        # prepare values for palette #3 and #4
        if isinstance(fog_color, str):
            pal3 = bytes.fromhex(str)[0:3]
        elif isinstance(fog_color,bytes):
            pal3 = fog_color[0:3]
        elif isinsntace(fog_color,Color):
            pal3 = fog_color.encode()
        else:
            pal3 = self.palette[9:12] # copy existing value
        
        if fog_intensity:
            pal4 = bytes(fog_intensity)
        else:
            pal4 = self.palette[12:15] # copy existing value
        
        # move over all entries and bitmap indices from #3 and #4
        pal = pal[0:9]+pal3+pal4+pal[9:]
        mip = bytearray(map(lambda x: x+2 if x>2 else x, mip))
        
        # replace data, clear other mips
        self.palette = pal[0:256]
        self.mip0, self.mip1, self.mip2, self.mip3 = (mip,None,None,None)
        
        return self # done
