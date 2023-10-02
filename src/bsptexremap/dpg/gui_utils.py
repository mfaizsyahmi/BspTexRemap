import dearpygui.dearpygui as dpg
import logging
from typing import NamedTuple
from enum import IntEnum
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
    content_stage_tag : int = None
def _x(): pass # this gets consumed by npp


def draw_crossed_rectangle(p1:tuple, p2:tuple, **kwargs):
    dpg.draw_rectangle(p1, p2, **kwargs)
    dpg.draw_line(p1, p2, **kwargs)
    dpg.draw_line((p2[0],p1[1]), (p1[0],p2[1]), **kwargs)


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
                    if item.content_stage_tag:
                        dpg.unstage(item.content_stage_tag)
                    else:
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
        logging.DEBUG:    (127,200,127), # ???
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
        try: dpg.configure_item(self._last_item,tracked=False)
        except: pass

        msg = self.format(record)
        self._last_item = dpg.add_text(
                msg, parent=DpgLogHandler.TAG, user_data=record, wrap=0,
                filter_key=record.levelno,
                color=DpgLogHandler.COLORS[record.levelno],
                tracked=True, track_offset=1)
        # scroll to end?
        #dpg.set_y_scroll(DpgLogHandler.TAG,dpg.get_y_scroll_max(DpgLogHandler.TAG))
        dpg.set_frame_callback(dpg.get_frame_count() + 2, self._untrack_all)

    def _untrack_all(self,*_):
        for item in dpg.get_item_children(DpgLogHandler.TAG,1):
            dpg.configure_item(item,tracked=False)


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


def __wtf(): pass

def show_loading(show=True):
    ''' shows a little window with a loading spinner at the bottom right corner '''
    TAG = "SPINNER_WINDOW"
    VAR_TAG = "var:SPINNER_WINDOW"

    if dpg.get_alias_id(TAG):
        dpg.configure_item(TAG,show=show)
        dpg.set_value(VAR_TAG, show)
    elif show:
        with dpg.value_registry():
            dpg.add_bool_value(tag=VAR_TAG, default_value=show)
        with dpg.window(tag=TAG, no_title_bar=True, no_resize=True,
                        min_size=[64,32]):
            with dpg.group(horizontal=True):
                dpg.add_loading_indicator(circle_count=8)
                dpg.add_text("Loading...")

    def _update_position(self, *_):
        if not dpg.get_value(VAR_TAG): return

        w_vp = dpg.get_viewport_client_width()
        h_vp = dpg.get_viewport_client_height()

        w = dpg.get_item_width(TAG)
        h = dpg.get_item_height(TAG)
        dpg.set_item_pos(TAG, [w_vp - w - 16, h_vp - h - 16])

        dpg.set_frame_callback(dpg.get_frame_count()+1,
                               callback=lambda:self(self))

    if show:
        dpg.set_frame_callback(dpg.get_frame_count()+1,
                               callback=lambda:_update_position(_update_position))


### MESSAGE BOX ----------------------------------------------------------------
class MsgBoxResult(IntEnum): # unused
    Cancel = 0
    OK = 1
    Yes = 2
    No = 3

def __wtf2(): pass


def wrap_message_box_callback(fn, *args,
                              _result_arg="confirm", _drop_on_false=True,
                              **kwargs):
    ''' given a function, returns a callable that a messagebox callback will call,
        adding the result of the message box in an arg of given name
        if drop on false is set, don't call back on false
    '''
    def wrap(sender, unused, user_data):
        # delete window
        dpg.delete_item(user_data[0])
        # drop the callback if user selected Cancel
        if not user_data[0] and _drop_on_false: return
        # else, call the function being wrapped
        fn(*args, **kwargs, **{_result_arg:user_data[1]})

    return wrap

def message_box(title, message, selection_callback:callable=None,
                buttons={True:"OK"}):
    ''' selection_callback must use a callback created with wrap_msgbox_callback
    '''
    if not selection_callback:
        selection_callback = wrap_message_box_callback(lambda *_,**__:True)

    # guarantee these commands happen in the same frame
    with dpg.mutex():

        viewport_width  = dpg.get_viewport_client_width()
        viewport_height = dpg.get_viewport_client_height()

        with dpg.window(label=title, modal=True, no_close=True) as modal_id:

            dpg.add_text()
            with dpg.group(horizontal=True):
                dpg.add_text(" ")
                dpg.add_text(message,wrap=500)
                dpg.add_text(" ")
            dpg.add_text()
            dpg.add_separator()

            with dpg.group(horizontal=True):
                for retval, label in buttons.items():
                    width = max(75,dpg.get_text_size(label)[0]+16)
                    dpg.add_button(label=label,
                                   width=width,
                                   user_data=(modal_id, retval),
                                   callback=selection_callback)

    # guarantee these commands happen in another frame
    dpg.split_frame()
    dpg.show_item(modal_id)
    dpg.split_frame()
    width = dpg.get_item_width(modal_id)
    height = dpg.get_item_height(modal_id)
    dpg.set_item_pos(modal_id, [viewport_width // 2 - width // 2, viewport_height // 2 - height // 2])


def confirm(title, message, selection_callback:callable):
    message_box(title, message, selection_callback,
                {True:"OK",False:"Cancel"})

def confirm_replace(filename, selection_callback:callable):
    confirm("Confirm file overwrite",
            f'"{filename}"\nFile already exists. Overwrite?',
            selection_callback)

