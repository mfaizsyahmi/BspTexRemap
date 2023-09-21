import dearpygui.dearpygui as dpg
from dataclasses import dataclass, field # TextureView
from itertools import chain

def flatten_imgdata(imgdata):
    return list(chain(*imgdata))

@dataclass
class TextureView:
    name:str
    width:int
    height:int
    channels:any        = None
    data:any            = None
    is_external:bool    = True
    # mat:str             = None
    uuid:int            = None

    @classmethod
    def from_img(cls, img, name):
        return cls(name, *img.size, 4, [n/256.0 for n in flatten_imgdata(miptex.to_image().convert("RGBA").getdata())] )
    
    @classmethod
    def from_miptex(cls, miptex):
        data = None
        if not miptex.is_external:
            data = flatten_imgdata(miptex.to_image().convert("RGBA").getdata())
            data = [n/256.0 for n in data]
        return cls(
                miptex.name,
                miptex.width,
                miptex.height,
                4 if not miptex.is_external else 0,
                data,
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

        return galleryItem
