import dearpygui.dearpygui as dpg
from collections import UserList # GalleryView

class GalleryView(UserList):
    ''' implementing a left-to-right, top-to-bottom gallery view of textures.
        the items stored must have the following methods:
        - estimate_group_width: to estimate the width
        - render: called to render the item
    '''
    spacing = 8
    scale = 1.0
    max_width = float('inf')
    
    def __init__(self):
        self.data = []
        with dpg.item_handler_registry() as resize_handler:
            dpg.add_item_resize_handler(callback=self.render)
        self._handler = resize_handler
    
    def _new_row(self, first=False):
        if not first: dpg.add_separator()
        return dpg.add_group(horizontal=True, horizontal_spacing=self.spacing)
        
    def render(self, data=None, datafilter=None, *args, **kwargs):
        if not data: data=self.data
        if datafilter: data = filter(datafilter,data)
    
        dpg.delete_item(self.parent, children_only=True)

        #win_w = dpg.get_item_width(self.parent)
        #win_w = dpg.get_item_rect_size(self.parent)[0]
        win_w = dpg.get_available_content_region(self.measureme)[0]
        
        dpg.push_container_stack(self.parent)
        row = self._new_row(True); 
        row_w, row_items = 0, 0
        for i, item in enumerate(data):
            item_w = item.estimate_group_width(self.scale, self.max_width)
            #print(f"img{i:03d} row_w/win_w:{row_w + self.spacing + item_w:-4d}/{win_w:-4d}")
            if row_items \
            and row_w + self.spacing + item_w > win_w:
                row = self._new_row()
                row_w, row_items = 0, 0
                
            dpg.push_container_stack(row)
            item.render(self.scale, self.max_width)
            dpg.pop_container_stack()
            
            row_w += self.spacing + item_w
            row_items += 1
            
        dpg.pop_container_stack()

    def submit(self, parent, measureme=None):
        self.parent = parent
        self.measureme = measureme or parent
        # dpg.bind_item_handler_registry(parent, resize_handler)
        # dpg.bind_item_handler_registry(dpg.last_root(), resize_handler)
