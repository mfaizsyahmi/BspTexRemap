import dearpygui.dearpygui as dpg
import logging
from typing import NamedTuple
from .colors import AppColors


# create_file_dialog
file_dlg_exts = {
    "bsp": ("BSP files (*.bsp){.bsp}",{"color":(0, 255, 255, 255)}),
    "txt": ("Text files (*.txt){.txt}",{"color":(0, 255, 255, 255)}),
    "all": ("All files (*.*){.*}",{})
}

def add_help_in_place(message):
    ''' adds a "(?)" next to the previous item, which displays the given tooltip
        message when hovered.
    '''
    last_item = dpg.last_item()
    group = dpg.add_group(horizontal=True)
    dpg.move_item(last_item, parent=group)
    dpg.capture_next_item(lambda s: dpg.move_item(s, parent=group))
    t = dpg.add_text("(?)", color=AppColors.Help.color)
    with dpg.tooltip(t):
        dpg.add_text(message)


def create_file_dialog(label,callback, exts,
        tag=None,
        directory_selector=False,
        show=False, modal=True,
        width=700 ,height=400):
    kwargs = {"tag":tag} if tag else {} # a way to optionally pass tag
    with dpg.file_dialog(
            label=label,
            directory_selector=directory_selector, 
            show=show, modal=modal,
            callback=callback, 
            width=width ,height=height,
            **kwargs) as dlg_tag:

        for ext_conf in exts:
            text = file_dlg_exts[ext_conf][0]
            kwargs = file_dlg_exts[ext_conf][1]
            dpg.add_file_extension(text, **kwargs)
            
    return dlg_tag


def populate_table(target, 
                   headers:list[str], 
                   data:list[list[str|tuple]]):
    ''' clears and repopulates target table
        header item can be label str or a tuple of label and weight
        cell item can be a text str or a tuple of text and kwargs dict
    '''    
    dpg.delete_item(target, children_only=True)
    dpg.push_container_stack(target)
    
    for this_header in headers:
        try:    label, weight = this_header # try unpack
        except: label, weight = this_header, 1
        dpg.add_table_column(label=label,init_width_or_weight=weight)
    
    for row in data:
        with dpg.table_row():
            for col in row:
                try:    text, kwargs = col     # try unpack
                except: text, kwargs = col, {}
                dpg.add_text(text,**kwargs)
    
    dpg.pop_container_stack()


class ImglistEntry(NamedTuple):
    image  : str|int
    width  : int
    height : int
    text   : list[str]
    key    : any  = 0 # sorting aid
def _x(): pass # this gets consumed by npp


def draw_crossed_rectangle(p1:tuple,p2:tuple):
    dpg.draw_rectangle(p1,p2)
    dpg.draw_line(p1,p2)
    dpg.draw_line((p2[0],p1[1]),(p1[0],p2[1]))


def populate_imglist(target, items:list[ImglistEntry], max_length=48, grow=False):
    ''' fills target item with a list of images with attached text
        item : [img_id, w,h, [*text]]
    '''
    dpg.delete_item(target, children_only=True)
    dpg.push_container_stack(target)
        
    try:
        for item in items:
            scale = min(max_length/item.width,max_length/item.height)
            factors = (scale,) if grow else (scale,1)
            w,h = item.width*min(*factors), item.height*min(*factors)
            x,y = max_length/2-w/2, max_length/2-h/2
                
            with dpg.group(horizontal=True):
                with dpg.drawlist(width=max_length,height=max_length):
                    if item.image is None:
                        draw_crossed_rectangle((0,0),(max_length,max_length))
                    else:
                        dpg.draw_image(item.image, (x,y), (x+w,y+h))
                with dpg.group():
                    for line in item.text:
                        dpg.add_text(line)
    finally:
        dpg.pop_container_stack()
    

def traverse_children(root, paths: str):
    ''' traverse item hierarchy by position 
        paths is in the form of "1.3.12" or "0:1.3"
        path part is separated by dot. slot is defined by #: before number
        traversal is on slot 1 by default
    '''
    parent = root
    for part in paths.split("."):
        slot, child = (1, part) if ":" not in part else part.split(":")
        try: parent = dpg.get_item_children(parent,slot=slot)[int(child)]
        except: return None
    return parent


def sort_table(sender, sort_specs):
    ''' sort_specs scenarios:
        1. no sorting -> sort_specs == None
        2. single sorting -> sort_specs == [[column_id, direction]]
        3. multi sorting -> sort_specs == [[column_id, direction], [column_id, direction], ...]
        
        notes:
        1. direction is ascending if == 1
        2. direction is ascending if == -1
    '''
    
    # no sorting case
    if sort_specs is None: return

    target_col = dpg.get_item_children(sender, 0).index(sort_specs[0][0])
    rows = dpg.get_item_children(sender, 1)

    # create a list that can be sorted based on first cell
    # value, keeping track of row and value used to sort
    sortable_list = []
    for row in rows:
        target_cell = dpg.get_item_children(row, 1)[target_col]
        sortable_list.append([row, dpg.get_value(target_cell)])

    def _sorter(e):
        return e[1]

    sortable_list.sort(key=_sorter, reverse=sort_specs[0][1] < 0)

    # create list of just sorted row ids
    new_order = []
    for pair in sortable_list:
        new_order.append(pair[0])
    
    dpg.reorder_items(sender, 1, new_order)


class DpgLogHandler(logging.Handler):
    COLORS = {
        logging.DEBUG:    (127,159,127), # olive
        logging.INFO:     (  0,160,255), # light blue
        logging.WARNING:  (255,127,  0), # orange
        logging.ERROR:    (255,  0,  0), # red
        logging.CRITICAL: (150,  0,255)  # purple
    }
    TAG = "log_console_window"
    
    def __init__(self, level=logging.NOTSET,**kwargs):
        super().__init__(level)
        try:
            dpg.add_window(tag=DpgLogHandler.TAG, label="Log Console",
                           width=420, height=200, **kwargs)
        except: pass
        
    def emit(self, record):
        msg = self.format(record)
        dpg.add_text(msg, parent=DpgLogHandler.TAG, user_data=record, wrap=0,
                     filter_key=record.levelno,
                     color=DpgLogHandler.COLORS[record.levelno])
        # scroll to end?
        dpg.set_y_scroll(DpgLogHandler.TAG,dpg.get_y_scroll_max(DpgLogHandler.TAG))


class DpgLogToTextItemHandler(logging.Handler):
    def __init__(self, target, level=logging.NOTSET, set_colors=False):
        super().__init__(level)
        self._target = target
        self._set_colors = set_colors
        
    def emit(self, record):
        msg = self.format(record)
        dpg.set_value(self._target,msg)
        
        dpg.configure_item(self._target, user_data=record)
        if self._set_colors:
            dpg.configure_item(self._target, color=DpgLogHandler.COLORS[record.levelno])


