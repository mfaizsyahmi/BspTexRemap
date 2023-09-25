import dearpygui.dearpygui as dpg
from . import dbgtools
from ..materials import MaterialSet
from .ntuple import ntuple
from .colors import MaterialColors, AppColors, AppThemes
from dataclasses import dataclass, field # TextureView
from itertools import chain
from typing import ClassVar
from logging import getLogger
log = getLogger(__name__)

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

    matname : str       = field(init=False) # post-initialized

    uuid : int          = field(init=False,default=None) # of the image
    _view_uuid : int    = field(init=False,default=None) # of the view widget
    selected : bool     = field(init=False,default=False) # view state

    # static reference to the app model to get the mat_set and wannabe_sets
    appdata : ClassVar       = None
    mat_update_cb : ClassVar = lambda *_: None

    # material choices. "-" is prepended to mean "not selected"
    matchars : ClassVar[str] = "-" + MaterialSet.MATCHARS
    # uneditable = lowercase
    matchars_disabled : ClassVar[str] = "_" + MaterialSet.MATCHARS.lower()

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
    def static_update(cls, tvitem, miptex, source_name, precedence=999):
        ''' class method provided for parallel thread processing '''
        tvitem.update_miptex(miptex,source_name,precedence)

    def __post_init__(self):
        self.matname = MaterialSet.strip(self.name).upper()
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

    @property
    def mat_editable(self): return self.matname not in TextureView.appdata.mat_set

    @property
    def mat(self):
        ''' returns material that matches itself '''
        for matset in (TextureView.appdata.mat_set,TextureView.appdata.wannabe_set):
            if (m := matset.get_mattype_of(self.matname)): break
        if self.mat_editable: return m if m else "-"
        return m.lower() if m else "_"

    @mat.setter
    def mat(self, val):
        if not self.mat_editable: return # can't edit
        # remove from existing sets
        for mat in TextureView.appdata.wannabe_set.MATCHARS:
            if mat == val: TextureView.appdata.wannabe_set[mat].add(self.matname)
            else: TextureView.appdata.wannabe_set[mat].discard(self.matname)

        # update view
        TextureView.mat_update_cb()


    def estimate_group_width(self, scale=1.0, max_length=float('inf')):
        return max( int(self.draw_size(scale, max_length)[0]),
                    int(dpg.get_text_size(self.name)[0]),
                    int(dpg.get_text_size(f"{self.width}x{self.height}")[0]) + 24,
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
        w_estimate = self.estimate_group_width(scale, max_length)
        w,h = self.draw_size(scale, max_length)
        mx_color= AppColors.External if self.is_external else AppColors.Embedded
        mx_theme= AppThemes.External if self.is_external else AppThemes.Embedded
        mx_text = "X" if self.is_external else "M"

        with dpg.group() as galleryItem:
            dpg.add_text(self.name,color=mx_color.color)
            #with dpg.popup(dpg.last_item(),mousebutton=dpg.mvMouseButton_Left):
            #    dpg.add_text(self.name,label="texture name")
            #    dpg.add_text(not self.is_external,label="embedded in BSP?")
            #    dpg.add_text(self.external_src,label="source WAD")
            #    dpg.add_text(self.matname,label="material name")
            #    dpg.add_text(not self.mat_editable,label="referenced in materials.txt?")
            #    dpg.add_text(not self.mat,label="assigned material")

            with dpg.drawlist(width=w, height=h):
                if self.uuid:
                    dpg.draw_image(self.uuid,(0,0),(w,h))
                else:
                    dpg.draw_rectangle((0,0),(w,h))
                    dpg.draw_line((0,0),(w,h))
                    dpg.draw_line((w,0),(0,h))

            with dpg.group(horizontal=True):
                dpg.add_text(f"{self.width}x{self.height}")
                dpg.add_button(label=mx_text,small=True,indent=w_estimate-16) #
                dpg.bind_item_theme(dpg.last_item(),mx_theme)

            # adds material selection slider
            # using a unique tag of the matname, we can link the values together
            linked_matval_tag = f"MATVAL:{self.matname}"
            try: # if successful, then it exists
                dpg.get_value(linked_matval_tag)
                kwargs={"source":linked_matval_tag}
            except: # it doesn't exist
                kwargs={"tag":linked_matval_tag}
            matslider = dpg.add_slider_int(
                    format="",width=w_estimate-16,
                    max_value=len(TextureView.matchars)-1,
                    default_value=0 if self.mat in "-_" \
                                  else TextureView.matchars.find(self.mat),
                    label=self.mat, # if self.mat_editable else self.mat.lower(),
                    enabled=self.mat_editable,
                    callback=self._slider_cb,**kwargs
            )
            if not self.mat_editable:
                dpg.bind_item_theme(matslider,AppThemes.Uneditable)

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
        # dpg.unstage(new_view)
        dpg_move_item(new_view, before=old_view)
        dpg.delete_item(old_view)
        dpg.delete_item(staging)

    def _slider_cb(self,sender,val):
        if not self.mat_editable: return
        self.mat = TextureView.matchars[val]
        dpg.configure_item(sender,label=TextureView.matchars[val])
        
        if not self.mat_editable:
            dpg.bind_item_theme(matslider,AppThemes.Uneditable)
        elif self.mat in "-_":
            dpg.bind_item_theme(sender,AppThemes.Material__)
        else:
            dpg.bind_item_theme(sender,AppThemes[f"Material_{self.mat}"])

