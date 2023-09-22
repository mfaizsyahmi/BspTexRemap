import dearpygui.dearpygui as dpg
from dataclasses import dataclass, field # TextureView
from itertools import chain

def flatten_imgdata(imgdata):
    return list(chain(*imgdata))
    
def img_to_dpg(img):
    return [n/256.0 for n in flatten_imgdata(img.convert("RGBA").getdata())]

@dataclass
class TextureView:
    name:str
    width:int
    height:int
    channels:any        = None
    data:any            = None
    is_external:bool    = True
    external_src:str    = None # holds name of wad file
    mat:str             = None # assigned material
    uuid:int            = None

    @classmethod
    def from_img(cls, img, name):
        return cls(name, *img.size, 4, img_to_dpg(miptex.to_image()) )
    
    @classmethod
    def from_miptex(cls, miptex):
        data = None if miptex.is_external else img_to_dpg(miptex.to_image())
        return cls(
                miptex.name, miptex.width, miptex.height,
                4 if not miptex.is_external else 0, data,
                miptex.is_external
        )

    def __post_init__(self):
        if not self.data: return
        with dpg.texture_registry():
            self.uuid = dpg.add_static_texture(
                width=self.width, height=self.height,
                default_value=self.data,
                label=self.name
            )
            
    def __del__(self):
        ''' make sure item is freed '''
        if self.uuid: dpg.delete_item(self.uuid)

    def update_miptex(self, miptex, source_name):
        ''' if found wad that has this texture, update here
        '''
        if self.name != miptex.name \
        or self.width != miptex.width \
        or self.height != miptex.height:
            raise ValueError("WAD miptex doesn't match BSP's miptex")
        
        self.external_src = source_name
        self.channels = 4
        self.data = img_to_dpg(miptex.to_image())
        self.__post_init__() # run this again now that we have data

    def estimate_group_width(self, scale=1.0, max_width=float('inf')):
        return max( int(min(self.width*scale,max_width)),
                    int(dpg.get_text_size(self.name)[0]) )

    def draw_size(self, scale=1.0, max_width=float('inf')):
        w = min(self.width * scale, max_width)
        h = self.height / self.width * w
        return (w,h)

    def render(self, scale=1.0, max_width=float('inf')):
        with dpg.group() as galleryItem:
            dpg.add_text(self.name)

            w,h = self.draw_size(scale, max_width)
            if self.uuid:
                dpg.add_image(self.uuid,width=w, height=h)
            else:
                with dpg.drawlist(width=w, height=h):
                    dpg.draw_rectangle((0,0),(w,h))
                    dpg.draw_line((0,0),(w,h))
                    dpg.draw_line((w,0),(0,h))

            dpg.add_text(f"{self.width}x{self.height}")
            if self.is_external:
                dpg.add_text(f"external")
            

        return galleryItem
