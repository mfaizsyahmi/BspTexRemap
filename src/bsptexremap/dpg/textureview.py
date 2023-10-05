import dearpygui.dearpygui as dpg
from . import dbgtools, gui_utils, consts
from ..materials import MaterialSet
from .ntuple import ntuple
from .colors import MaterialColors, AppColors, AppThemes
from dataclasses import dataclass, field # TextureView
from itertools import chain
from typing import ClassVar
from logging import getLogger
import re
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
    _handlers_initialized  = False


    ## static reference to the app model to get the mat_set and wannabe_sets
    app : ClassVar = None
    mat_update_cb : ClassVar = lambda *_: None
    mouse_event_registrar : ClassVar = None

    ## material choices. "-" is prepended to mean "not selected"
    ## Please call class_set_matchars to properly set all of these
    matchars_base : ClassVar[str] = MaterialSet.MATCHARS
    matchars : ClassVar[str] = "-" + MaterialSet.MATCHARS
    # uneditable = lowercase
    matchars_disabled : ClassVar[str] = "_" + MaterialSet.MATCHARS.lower()

    @classmethod
    def class_init(cls, app, mat_update_cb, mouse_event_registrar, global_texture_registry):
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
        cls.global_texture_registry = global_texture_registry

        ## the popup for embedded/external button
        with dpg.window(tag="TEXVIEW:POPUP", popup=True, 
                        show=False, autosize=True,
                        min_size=(80,20)) as mx_popup:
            # width is arbitrarym as dpg.get_text_size is unavailable at the point of execution
            mx_list = dpg.add_listbox(consts.TEXVIEW_MX,num_items=2,width=80)
            
        dpg.bind_item_theme(mx_popup,"theme:_popup")
        
        cls._mx_popup = mx_popup
        cls._mx_list = mx_list


    @classmethod
    def class_set_matchars(cls, matchars):
        cls.matchars_base = matchars.upper()
        cls.matchars      = "-" + cls.matchars_base
        cls.matchars_disabled = "_" + cls.matchars_base.lower()

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

        if self.data:
            dpg.push_container_stack(TextureView.global_texture_registry)
            try:
                self.uuid = dpg.add_static_texture(
                    width=self.width, height=self.height,
                    default_value=self.data,
                    label=self.name
                )
            except Exception as e:
                log.warning(f"Failed to load texture image for: {self.name}\n{e}")
            finally:
                dpg.pop_container_stack()


    def _init_handlers(self):
        ''' handlers for the rendered dpg items, created once per lifetime.
            it's easier to have handlers per instance, as it's cumbersome to get
            instance reference from class handlers.
        '''

        ## gallery item hover
        with dpg.item_handler_registry() as gallery_hover_tracker:
            dpg.add_item_hover_handler(callback=lambda:self._on_hover(True))
        self.gallery_hover_tracker = gallery_hover_tracker

        ## material slider
        with dpg.item_handler_registry() as matslider_hover_handler:
            dpg.add_item_hover_handler(callback=lambda:self._slider_hover())
        self.matslider_hover_handler = matslider_hover_handler

        ## embed/extern button click
        with dpg.item_handler_registry() as mx_button_handler:
            dpg.add_item_clicked_handler(callback=lambda:self._mx_button_click())
        self.mx_button_handler = mx_button_handler

        self._handlers_initialized = True


    def __del__(self):
        ''' make sure all items are freed '''
        if self._handlers_initialized:
            dpg.delete_item(self.gallery_hover_tracker)
            dpg.delete_item(self.matslider_hover_handler)
            dpg.delete_item(self.mx_button_handler)
        if self.uuid:
            try: dpg.delete_item(self.uuid)
            except: pass


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
        self.precedence = precedence
        self.__post_init__() # run this again now that we have data

    @property # to help with my sanity
    def is_embedded(self): return not self.is_external

    @property
    def mat_editable(self):
        return (self.become_external==False or self.is_external==False) \
        and not re.match(consts.TEX_IGNORE_RE, self.name)
        #and self.matname not in TextureView.app.data.mat_set

    @property
    def mat(self):
        ''' returns material that matches itself '''
        for matset in (TextureView.app.data.wannabe_set,TextureView.app.data.mat_set):
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
                    int(dpg.get_text_size(f"{self.width}x{self.height}")[0]) + 24 )

    def draw_size(self, scale=1.0, max_length=float('inf')):
        max_scale = min(max_length/self.width,max_length/self.height)
        w = self.width * min(scale, max_scale)
        h = self.height * min(scale, max_scale)
        return (w,h)

    def render(self, scale=1.0, max_length=float('inf')):
        if not self._handlers_initialized:
            self._init_handlers()

        #with dpg.child_window(width=w) as galleryItem:
        w_estimate = self.estimate_group_width(scale, max_length)
        w,h = self.draw_size(scale, max_length)
        ch = dpg.get_text_size("X")[1] # char height, used to estimate checkbox size

        with dpg.group(user_data=[self.matname,self]) as galleryItem: #

            ## first row: texture name
            with dpg.group(horizontal=True) as first_row:
                # probably change this to a button, as popups probably needs one
                self._label_uuid = dpg.add_text(self.name)
                
                with dpg.tooltip(first_row, delay=0.5):
                    with dpg.table(header_row=False,borders_innerV=True) as tooltip_table:
                        dpg.add_table_column(); dpg.add_table_column()
                        with dpg.table_row():
                            dpg.add_text("material name")
                            dpg.add_text(self.matname)
                        with dpg.table_row():
                            dpg.add_text("is external")
                            dpg.add_text(self.is_external)
                        with dpg.table_row():
                            dpg.add_text("source WAD")
                            dpg.add_text(self.external_src)
                        with dpg.table_row():
                            dpg.add_text("precedence")
                            dpg.add_text(self.precedence)
                self._ttt_uuid = tooltip_table

                self._selector_uuid = dpg.add_checkbox(
                        indent=w_estimate-ch-6, show=False,
                        callback=self._select_cb,
                        **self._get_tag_and_source_kwargs("TEXSELECT")
                )

            ## second row: image
            with dpg.drawlist(width=w, height=h):
                if self.uuid:
                    dpg.draw_image(self.uuid,(0,0),(w,h))
                else:
                    gui_utils.draw_crossed_rectangle((0,0),(w,h))

                with dpg.draw_layer(show=False) as overlay_to_embed: # green plus
                    dpg.draw_rectangle((0,0),(w,h),color=(0,255,0))  # rectangle
                    dpg.draw_rectangle((0,0),(16,16),color=(0,255,0))
                    dpg.draw_line((0,8),(16,8),color=(0,255,0)) # horz line
                    dpg.draw_line((8,0),(8,16),color=(0,255,0)) # vert line
                self._layer_to_embed = overlay_to_embed

                with dpg.draw_layer(show=False) as overlay_to_unembed: # red cross
                    dpg.draw_rectangle((0,0),(w,h),color=(255,0,0))
                    gui_utils.draw_crossed_rectangle((0,0),(16,16),color=(255,0,0))
                self._layer_to_unembed = overlay_to_unembed

                with dpg.draw_layer(show=False) as overlay_selected:
                    dpg.draw_rectangle((0,0),(w,h),color=AppColors.Selected.bg)
                self._layer_selected = overlay_selected

            ## third row: dims, embedded/external indicator
            with dpg.group(horizontal=True):
                dpg.add_text(f"{self.width}x{self.height}")
                mx_btn = dpg.add_button(label="-",small=True,indent=w_estimate-16)
            self._mx_btn = mx_btn
            dpg.bind_item_handler_registry(mx_btn, self.mx_button_handler)

            ## last row: material slider
            matslider = dpg.add_slider_int(
                    format="",width=w_estimate-16,
                    max_value=len(TextureView.matchars)-1,
                    default_value=0 if self.mat in "-_" \
                                  else TextureView.matchars.find(self.mat.upper()),
                    label=self.mat,
                    enabled=self.mat_editable,
                    callback=self._slider_cb,
                    # stuff the tag and source values
                    **self._get_tag_and_source_kwargs("MATVAL")
            )
            self._slider_uuid = matslider
            dpg.bind_item_handler_registry(matslider, self.matslider_hover_handler)

        self._view_uuid = galleryItem
        dpg.bind_item_handler_registry(galleryItem, self.gallery_hover_tracker)

        ## applies the state and theme
        self.update_state()

        return galleryItem

    def _get_tag_and_source_kwargs(self,prefix="MATVAL"):
        ''' a common function to get a tag name that's unique but also related,
            such that related tags share the same prefix, with differing suffix,
            so it takes the form of:
                {PREFIX}{fixed width material name}{index}

            then the first of such series is designated the primary source tag
            and all the other items point to it for their source value.

            returns a kwargs dict containing tag (+source) that you can tag onto
            an add_item call.
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

    def update_state(self):
        ''' sets labels, show/hide stuff, applies themes '''

        ### Get values ---------------------------------------------------------
        ## label
        label_color = AppColors.External if self.is_external else AppColors.Embedded

        ## mx button
        if self.become_external is not None:
            mx_color= AppColors.ToUnembed if self.become_external else AppColors.ToEmbed
            mx_theme= AppThemes.ToUnembed if self.become_external else AppThemes.ToEmbed
            mx_text = "X" if self.become_external else "M"
        else:
            mx_color= AppColors.External if self.is_external else AppColors.Embedded
            mx_theme= AppThemes.External if self.is_external else AppThemes.Embedded
            mx_text = "X" if self.is_external else "M"

        ## matslider
        slider_val = 0 if self.mat in "-_" \
                     else TextureView.matchars.find(self.mat.upper())
        slider_theme = AppThemes.Uneditable if not self.mat_editable \
                       else AppThemes.Material__ if self.mat in "-_" \
                       else AppThemes[f"Material_{self.mat}"]

        ## selection theme
        selection_theme = AppThemes.Selected if self.selected else AppThemes.Normal

        try:
            ### Apply theme/state --------------------------------------------------
            ## label
            dpg.configure_item(self._label_uuid,color=label_color.color)
    
            ## mx button/state
            dpg.configure_item(self._mx_btn, label=mx_text) #, color=mx_color.color)
            dpg.bind_item_theme(self._mx_btn, mx_theme)
            dpg.configure_item(self._layer_to_embed, show=self.become_external==False)
            dpg.configure_item(self._layer_to_unembed, show=self.become_external==True)
    
            ## matslider
            dpg.configure_item(self._slider_uuid,label=self.mat,enabled=self.mat_editable)
            dpg.set_value(self._slider_uuid,slider_val)
            dpg.bind_item_theme(self._slider_uuid,slider_theme)
    
            ## selected state
            dpg.bind_item_theme(self._view_uuid,selection_theme)
            dpg.configure_item(self._selector_uuid, show=self.selected)
            dpg.configure_item(self._layer_selected, show=self.selected)
            dpg.set_value(self._selector_uuid,self.selected)
        except: pass

    def update_relatives_state(self):
        ''' updates selection/material/embed state of all related textures 
        '''
        with dpg.mutex():
            for item in TextureView.app.view.textures:
                if item.matname != self.matname: continue

                if item != self:
                    item.selected = self.selected # select the other entries
                    item.become_external = self.become_external

                item.update_state()


    def set_embed(self, target_state:bool):
        ''' sets the become_external prop, except that the target value is the
            opposite to be in line with the convention on the gui
        '''
        # check that we are allowed to unembed
        if not TextureView.app.data.allow_unembed \
        and self.is_embedded and not target_state:
            log.error("Current settings disallow unembedding textures! Discarding change.")
            return
        # check that we know where the source of the external textures are
        elif not self.external_src and target_state:
            log.error("The external WAD source for this texture is unknown. Please load them first.")
            return
        
        log.info(f"change embed state of {self.matname} to {target_state}")
        # same state as original -> unset
        if target_state == self.is_embedded:
            self.become_external = None
        else:
            self.become_external = not target_state

        self.update_relatives_state()
    

    ## embed/extern button click callback
    def _mx_button_click(self,*_):
        val_map = {False:0, True:1}
        val = consts.TEXVIEW_MX[val_map[self.become_external]] \
              if self.become_external is not None \
              else consts.TEXVIEW_MX[val_map[self.is_external]]
    
        width = max(*(dpg.get_text_size(x)[0] for x in consts.TEXVIEW_MX)) + 24
        dpg.set_value(TextureView._mx_list, val)
        dpg.configure_item(TextureView._mx_list, width=width)
        dpg.set_item_callback(TextureView._mx_list, self._mx_cb)
        
        dpg.configure_item(TextureView._mx_popup, show=True)

    def _mx_cb(self, sender, data):
        dpg.configure_item(TextureView._mx_popup, show=False)

        val_map = {0:False, 1:True}
        data = val_map[consts.TEXVIEW_MX.index(data)] if isinstance(data,str) else data

        # check that we are allowed to unembed
        if not TextureView.app.data.allow_unembed \
        and not self.is_external and data:
            log.error("Current settings disallow unembedding textures! Discarding change.")
            return
        # check that we know where the source of the external textures are
        elif not self.external_src and data:
            log.error("The external WAD source for this texture is unknown. Please load them first.")
            return

        
        log.info(f"change embed state of {self.matname} to {not data}")
        # same state as original -> unset
        if data == self.is_external:
            self.become_external = None
        else:
            self.become_external = data

        self.update_relatives_state()


    ## matslider hovered callback
    def _slider_hover(self,*_):
        TextureView.mouse_event_registrar(self._slider_uuid, {
            "mouse_wheel": lambda data: self._slider_cb(0,data)
        })

    ## matslider value change callback
    def _slider_cb(self,sender,val):
        if not self.mat_editable: return

        if sender==0: # from wheel event
            # we used to add dpg.get_value() to the delta in the callback
            # but that produced wonky results
            # so we pass delta directly, and calculate value here

            # only work when ctrl key is down (to avoid gallery window scrolling)
            if not dpg.is_key_down(dpg.mvKey_Control): return

            val += 0 if self.mat in "-_" else TextureView.matchars.find(self.mat.upper())
            # wrap around on the positive side, because it does so
            # automatically on the negative side
            if val >= len(TextureView.matchars):
                val %= len(TextureView.matchars)
            dpg.set_value(self._slider_uuid,val)

        self.mat = TextureView.matchars[val]

        self.update_relatives_state()


    ## checkbox callback
    def _select_cb(self,sender,val=False):
        self.selected=val
        self.update_relatives_state()


    ## gallery item hover event handler
    def _on_hover(self, hovering=True):
        if hovering:
            dpg.configure_item(self._selector_uuid, show=True)
            dpg.set_frame_callback(dpg.get_frame_count()+1, lambda:self._on_hover(False))
        elif not self.selected:
            dpg.configure_item(self._selector_uuid, show=False)

