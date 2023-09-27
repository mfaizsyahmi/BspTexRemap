import dearpygui.dearpygui as dpg
from . import dbgtools, gui_utils
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
    channels : any         = None
    data : any             = None
    is_external : bool     = True # initial state of embedded/external
    external_src : str     = None # holds name of wad file
    precedence : int       = 1000 # for overloading wad textures

    matname : str          = field(init=False) # post-initialized
    become_external : bool = field(init=False,default=None) # target state

    uuid : int             = field(init=False,default=None) # of the image
    _view_uuid : int       = field(init=False,default=None) # of the view widget
    selected : bool        = field(init=False,default=False) # view state

    ## static reference to the app model to get the mat_set and wannabe_sets
    app : ClassVar = None
    mat_update_cb : ClassVar = lambda *_: None
    mouse_event_registrar : ClassVar = None

    ## material choices. "-" is prepended to mean "not selected"
    matchars : ClassVar[str] = "-" + MaterialSet.MATCHARS
    # uneditable = lowercase
    matchars_disabled : ClassVar[str] = "_" + MaterialSet.MATCHARS.lower()

    @classmethod
    def class_init(cls, app, mat_update_cb, mouse_event_registrar):
        ''' inits class vars and inserts the static components (e.g. handlers and popups)
            app = reference to app
            collection = reference to the list where all the instances are
                         (e.g. app.view.textures)
            mat_update_cb is callback when materials are changed
            (used to call update_wannabe_material_tables)
        '''
        cls.app = app # used to get/set materials
        cls.mat_update_cb = mat_update_cb
        cls.mouse_event_registrar = mouse_event_registrar

        with dpg.item_handler_registry() as mouse_hover_tracker:
            dpg.add_item_hover_handler(callback=cls.static_item_hover_handler)

        cls.mouse_hover_tracker = mouse_hover_tracker

    @classmethod
    def static_item_hover_handler(cls,sender,target):
        ''' this fn is continuously called when the target is hovered
            target is the item being hovered
        '''
        if dpg.get_item_alias(target).startswith("MATVAL:"):
            cls.mouse_event_registrar(target,{
                "mouse_wheel": lambda data:\
                    dpg.get_item_callback(target)(0,data) # dpg.get_value(target)
            })
        elif dpg.get_item_user_data(target)[1]._view_uuid == target:
            dpg.get_item_user_data(target)[1]._on_hover(True)


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
            but only if precedence is higher than the last
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
    def mat_editable(self): return self.matname not in TextureView.app.data.mat_set

    @property
    def mat(self):
        ''' returns material that matches itself '''
        for matset in (TextureView.app.data.mat_set,TextureView.app.data.wannabe_set):
            if (m := matset.get_mattype_of(self.matname)): break
        if self.mat_editable: return m if m else "-"
        return m.lower() if m else "_"

    @mat.setter
    def mat(self, val):
        if not self.mat_editable: return # can't edit
        # remove from existing sets
        for mat in TextureView.app.data.wannabe_set.MATCHARS:
            if mat == val: TextureView.app.data.wannabe_set[mat].add(self.matname)
            else: TextureView.app.data.wannabe_set[mat].discard(self.matname)

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

        with dpg.group(user_data=[self.matname,self]) as galleryItem: #
            ## first row: texture name
            with dpg.group(horizontal=True):
                # probably change this to a button, as popups probably needs one
                dpg.add_text(self.name,color=mx_color.color)

                self._selector_uuid = dpg.add_checkbox(
                        indent=w_estimate-20,show=False,
                        callback=self._select_cb,
                        **self._get_tag_and_source_kwargs("TEXSELECT")
                )

            ## second row: image, and selected checkbox (show on hover)
            with dpg.group(horizontal=True):
                with dpg.drawlist(width=w, height=h):
                    if self.uuid:
                        dpg.draw_image(self.uuid,(0,0),(w,h))
                    else:
                        gui_utils.draw_crossed_rectangle((0,0),(w,h))
                    if self.become_external:
                        gui_utils.draw_crossed_rectangle((0,0),(w,h),color=(255,0,0))
                        #dpg.draw_rectangle((0,0),(w,h))
                        #dpg.draw_line((0,0),(w,h))
                        #dpg.draw_line((w,0),(0,h))


            with dpg.group(horizontal=True):
                dpg.add_text(f"{self.width}x{self.height}")
                dpg.add_button(label=mx_text,small=True,indent=w_estimate-16) #
                dpg.bind_item_theme(dpg.last_item(),mx_theme)

            # inserts the material slider
            matslider = dpg.add_slider_int(
                    format="",width=w_estimate-16,
                    max_value=len(TextureView.matchars)-1,
                    default_value=0 if self.mat in "-_" \
                                  else TextureView.matchars.find(self.mat.upper()),
                    label=self.mat, # if self.mat_editable else self.mat.lower(),
                    enabled=self.mat_editable,
                    callback=self._slider_cb,
                    # stuff the tag and source values
                    **self._get_tag_and_source_kwargs("MATVAL")
            )
            dpg.bind_item_theme(matslider,self._slider_get_theme())
            dpg.bind_item_handler_registry(matslider, TextureView.mouse_hover_tracker)
            self._slider_uuid = matslider

        dpg.bind_item_handler_registry(galleryItem, TextureView.mouse_hover_tracker)
        dpg.bind_item_theme(galleryItem,self._selection_theme())
        self._view_uuid = galleryItem

        return galleryItem

    def _get_tag_and_source_kwargs(self,prefix="MATVAL"):
        ''' a common function to get a tag name that's unique but also regular,
            such that related tags share the same prefix, with differing suffix
            then the first of such series is designated the primary source tag
            and all the other items point to it for their source value

            prepares tags/sources for the material slider. it should be unique
            but related, so it takes the form of
                {PREFIX}{fixed width material name}{index}
            this is to facilitate updating all the related material's mat values

            returns a kwargs dict containing tag (+source) that you can tag onto
            a add_item call
        '''
        kwargs={}
        for i in range(32): # finding next empty unique tag
            if i: kwargs["source"]=f"{prefix}:{self.matname:15s}0"
            candidate_tag = f"{prefix}:{self.matname:15s}{i}"
            if not dpg.get_alias_id(candidate_tag):
                kwargs["tag"] = candidate_tag
                break
        return kwargs


    def render_in_place(self, *args, **kwargs):
        old_view = self._view_uuid
        # make sre that the referenced item exists (i.e. it's being rendered)
        try: dpg.get_item_width(old_view)
        except: return

        with dpg.stage() as staging:
            new_view = self.render(*args, **kwargs) # self-assigns _view_uuid
        # dpg.unstage(new_view)
        dpg_move_item(new_view, before=old_view)
        dpg.delete_item(old_view)
        dpg.delete_item(staging)

    def _selection_theme(self):
        return AppThemes.Selected if self.selected else AppThemes.Normal

    def _slider_get_theme(self):
        if not self.mat_editable:
            return AppThemes.Uneditable
        elif self.mat in "-_":
            return AppThemes.Material__
        else:
            return AppThemes[f"Material_{self.mat}"]

    def update_relatives_state(self):
        ''' updates selection/material/embed state of all related textures '''
        target_selection_theme = self._selection_theme()
        target_slider_theme = self._slider_get_theme()
        slider_label = self.mat
        slider_val = 0 if self.mat in "-_" else TextureView.matchars.find(self.mat.upper())

        with dpg.mutex():
            for item in TextureView.app.view.textures:
                if item.matname != self.matname: continue
                if item != self:
                    item.selected = self.selected # select the other entries

                dpg.bind_item_theme(item._view_uuid,target_selection_theme)

                dpg.configure_item(item._slider_uuid,label=slider_label)
                dpg.set_value(item._slider_uuid,slider_val)
                dpg.bind_item_theme(item._slider_uuid,target_slider_theme)

                dpg.configure_item(self._selector_uuid, show=self.selected)
                dpg.set_value(item._selector_uuid,self.selected)


    def _slider_cb(self,sender,val):
        if not self.mat_editable: return
        if sender==0: # from wheel event
            # we used to add dpg.get_value() to the delta in the callback
            # but that produced wonky results
            # so we pass delta directly, and calculate value here
            if not dpg.is_key_down(dpg.mvKey_Control): return
            val += 0 if self.mat in "-_" else TextureView.matchars.find(self.mat.upper())
            # wrap around on the positive side, because it does so 
            # automatically on the negative side
            if val >= len(TextureView.matchars):
                val %= len(TextureView.matchars)
            dpg.set_value(self._slider_uuid,val)

        self.mat = TextureView.matchars[val]

        self.update_relatives_state()
        '''
        label = TextureView.matchars[val]
        target_theme = self._slider_get_theme()

        # update all linked material names
        for i in range(32):
            tag = f"MATVAL:{self.matname:15s}{i}"
            if not dpg.get_alias_id(tag): break

            dpg.configure_item(tag,label=label)
            dpg.bind_item_theme(tag,target_theme)
        '''

    def _select_cb(self,sender,val=False): # checkbox callback
        self.selected=val
        self.update_relatives_state()
        '''
        target_theme = self._selection_theme()

        # apply selection and theme to all related textures of the same matname
        for item in TextureView.app.view.textures:
            if item.matname != self.matname: continue
            if item != self: item.selected = val # select the other entries
            dpg.set_value(item._selector_uuid,val)
            dpg.bind_item_theme(item._view_uuid,target_theme)
        '''

    def _on_hover(self, hovering=True):
        if hovering:
            dpg.configure_item(self._selector_uuid, show=True)
            dpg.set_frame_callback(dpg.get_frame_count()+1, lambda:self._on_hover(False))
        elif not self.selected:
            dpg.configure_item(self._selector_uuid, show=False)
