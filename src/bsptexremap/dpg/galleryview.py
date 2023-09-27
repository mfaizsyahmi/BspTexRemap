import dearpygui.dearpygui as dpg
from collections import UserList
from itertools import chain
from .dbgtools import time_it
import logging

log = logging.getLogger(__name__)


class GalleryView(UserList):
    ''' implementing a left-to-right, top-to-bottom gallery view of textures.
        the items stored must have the following methods:
        - estimate_group_width: to estimate the width
        - render: called to render the item
    '''
    spacing = 8

    scale = 1.0               # set by gallery_size_val_map
    max_length = float('inf') # ditto

    def __init__(self):
        self.data = [] # texview items go here
        self._items = [] # uuids of rendered texview items go her

        with dpg.item_handler_registry() as handler:
            #dpg.add_item_clicked_handler(callback=lambda s,a,u:print("clicked",s,a,u))
            #dpg.add_item_hover_handler(callback=)
            #dpg.add_item_resize_handler(callback=self.render)
            pass

        self._handler = handler
        self._render_on_frame = None

    def _new_row(self, first=False):
        if not first: dpg.add_separator()
        return dpg.add_group(horizontal=True, horizontal_spacing=self.spacing)

    def render(self, data=None, datafilter=None, *args, **kwargs):
        # an attempt at throttling render calls
        if not data and not datafilter \
        and self._render_on_frame == dpg.get_frame_count(): return

        if not data: data=self.data
        if datafilter: data = filter(datafilter,data)

        self._render_on_frame = dpg.get_frame_count()
        dpg.delete_item(self.parent, children_only=True)

        #win_w = dpg.get_item_width(self.parent)
        #win_w = dpg.get_item_rect_size(self.parent)[0]
        win_w = dpg.get_available_content_region(self.measureme)[0]

        i, end = 0, len(data)
        self._items = []
        with time_it():
            log.debug("RENDERING GALLERY")
            dpg.push_container_stack(self.parent)
            with dpg.mutex():
                while i < end:
                    if i: dpg.add_separator()
                    with dpg.group(horizontal=True, horizontal_spacing=self.spacing):
                        row_w, row_items = 0, 0
                        while i < end:
                            row_w += self.spacing \
                                  + data[i].estimate_group_width(self.scale, self.max_length)
                            if row_items and row_w > win_w: break
                            self._items.append(data[i].render(self.scale, self.max_length))
                            i += 1; row_items += 1

            dpg.pop_container_stack()
        '''
        row = self._new_row(True);
        row_w, row_items = 0, 0
        for i, item in enumerate(data):
            item_w = item.estimate_group_width(self.scale, self.max_length)
            if row_items \
            and row_w + self.spacing + item_w > win_w:
                row = self._new_row()
                row_w, row_items = 0, 0

            dpg.push_container_stack(row)
            self._items.append(item.render(self.scale, self.max_length))
            dpg.pop_container_stack()

            row_w += self.spacing + item_w
            row_items += 1
        dpg.pop_container_stack()
        '''


    def reflow(self): # DON'T USE, BUGGY AF
        # redirect to render until we can sort this out
        return self.render()

        win_w = dpg.get_available_content_region(self.measureme)[0]

        rows = tuple(r for r in dpg.get_item_children(self.parent,1) if dpg.is_item_container(r))
        items = tuple(chain(*(dpg.get_item_children(row,1) for row in rows)))
        item_widths = tuple(dpg.get_item_rect_size(item)[0] for item in items)

        target_row_slots = []
        row_w, row_count = 0,0
        row_start = 0
        for i,item in enumerate(items):
            row_w += item_widths[i] + self.spacing
            if row_count and row_w > win_w:
                target_row_slots += [items[row_start:i]]
                row_start = i
                row_w, row_count = 0,0
            row_count += 1


        for j, row_slot in enumerate(target_row_slots):
            if j < len(rows):
                for item in row_slot:
                    dpg.move_item(item,parent=rows[j])
            else:
                with dpg.row(parent=self.parent) as newrow:
                    for item in row_slot:
                        dpg.move_item(item,parent=newrow)


    def submit(self, parent, measureme=None):
        self.parent = parent
        self.measureme = measureme or parent
        dpg.bind_item_handler_registry(self.measureme, self._handler)
        # dpg.bind_item_handler_registry(dpg.last_root(), resize_handler)

    def on_drag_start(self,sender,data):
        pos = dpg.get_mouse_pos()
        print("start_drag",pos,sender,data)
    def on_drag_end(self,sender,data):
        print("start_drag",pos,sender,data)

