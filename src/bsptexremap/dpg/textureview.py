import dearpygui.dearpygui as dpg
from dataclasses import dataclass, field # TextureView
from itertools import chain
from .ntuple import ntuple

def flatten_imgdata(imgdata):
    return list(chain(*imgdata))

def img_to_dpg(img):
    return [n/256.0 for n in flatten_imgdata(img.convert("RGBA").getdata())]

@dataclass
class TextureView:
    name : str
    width : int
    height : int
    channels : any      = None
    data : any          = None
    is_external : bool  = True
    external_src : str  = None # holds name of wad file
    precedence : int    = 1000 # for overloading wad textures
    mat : str           = None # assigned material
    uuid : int          = None # of the image
    _view_uuid : int    = None # of the view widget
    selected : bool     = False # view state

    @classmethod
    def from_img(cls, img, name):
        return cls(name, *img.size, 4, img_to_dpg(miptex.to_image()) )

    @classmethod
    def from_miptex(cls, miptex):
        data = None if miptex.is_external else img_to_dpg(miptex.to_image())
        return cls(
                miptex.name, miptex.width, miptex.height,
                4 if not miptex.is_external else 0, data,
                miptex.is_external,
                # ...skipping a few items...
                precedence = -1 if not miptex.is_external else 1000
        )

    @classmethod
    def static_update(cls, tvitem, miptex, source_name):
        ''' class method provided for parallel thread processing '''
        tvitem.update_miptex(miptex,source_name)

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

    def update_miptex(self, miptex, source_name, precedence=999):
        ''' if found wad that has this texture, update here
            todo: precedence overload if higher than current
        '''
        # if self.name != miptex.name # SKIPS NAME CHECK FOR NOW
        if False \
        or self.width != miptex.width \
        or self.height != miptex.height:
            raise ValueError("WAD miptex doesn't match BSP's miptex")

        elif self.precedence <= precedence: return

        self.external_src = source_name
        self.channels = 4
        self.data = img_to_dpg(miptex.to_image())
        self.precedende = precedence
        self.__post_init__() # run this again now that we have data


    def estimate_group_width(self, scale=1.0, max_length=float('inf')):
        return max( int(self.draw_size(scale, max_length)[0]),
                    int(dpg.get_text_size(self.name)[0]),
                    int(dpg.get_text_size(f"{self.width}x{self.height}")[0]),
                    int(dpg.get_text_size("external")[0]), # temp
                    )

    def draw_size(self, scale=1.0, max_length=float('inf')):
        # w = min(self.width * scale, max_length)
        # h = self.height / self.width * w

        max_scale = min(max_length/self.width,max_length/self.height)
        w = self.width * min(scale, max_scale)
        h = self.height * min(scale, max_scale)
        return (w,h)

    def render(self, scale=1.0, max_length=float('inf')):
        #with dpg.child_window(width=w) as galleryItem:
        with dpg.group() as galleryItem:
            w,h = self.draw_size(scale, max_length)
            dpg.add_text(self.name)

            with dpg.drawlist(width=w, height=h):
                if self.uuid:
                    dpg.draw_image(self.uuid,(0,0),(w,h))
                else:
                    dpg.draw_rectangle((0,0),(w,h))
                    dpg.draw_line((0,0),(w,h))
                    dpg.draw_line((w,0),(0,h))

            dpg.add_text(f"{self.width}x{self.height}")
            if self.is_external:
                dpg.add_text("external")

        dpg.bind_item_theme(galleryItem,"theme:galleryitem_normal")
        self._view_uuid = galleryItem
        return galleryItem

    def render_in_place(self, *args, **kwargs):
        old_view = self._view_uuid
        # make sre that the referenced item exists (i.e. it's being rendered)
        try: dpg.get_item(old_view)
        except: return

        with dpg.stage() as staging:
            new_view = self.render(*args, **kwargs) # self-assigns _view_uuid
        dpg.unstage(new_view)
        dpg_move_item(new_view, before=old_view)
        dpg.delete_item(old_view)
        dpg.delete_item(staging)

