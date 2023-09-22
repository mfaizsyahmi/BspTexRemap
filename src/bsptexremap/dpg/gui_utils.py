import dearpygui.dearpygui as dpg

# create_file_dialog
file_dlg_exts = {
    "bsp": ("BSP files (*.bsp){.bsp}",{"color":(0, 255, 255, 255)}),
    "txt": ("Text files (*.txt){.txt}",{"color":(0, 255, 255, 255)}),
    "all": ("All files (*.*){.*}",{})
}

def _help(message):
    ''' adds a "(?)" next to the previous item, which displays the given tooltip
        message when hovered.
    '''
    last_item = dpg.last_item()
    group = dpg.add_group(horizontal=True)
    dpg.move_item(last_item, parent=group)
    dpg.capture_next_item(lambda s: dpg.move_item(s, parent=group))
    t = dpg.add_text("(?)", color=[0, 255, 0])
    with dpg.tooltip(t):
        dpg.add_text(message)

def create_file_dialog(label,tag, callback, exts,
        directory_selector=False, 
        show=False, modal=True,
        width=700 ,height=400):
    with dpg.file_dialog(
            label=label,
            tag=tag, 
            directory_selector=directory_selector, 
            show=show, modal=modal,
            callback=callback, 
            width=width ,height=height):
        for ext_conf in exts:
            text = file_dlg_exts[ext_conf][0]
            kwargs = file_dlg_exts[ext_conf][1]
            dpg.add_file_extension(text, **kwargs)

def _sort_table(sender, sort_specs):
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

def _toggle_prop(sender,app_data,user_data,app=None):
    app.togglers.add(sender)
    dpg.set_value(user_data, app_data)
    app.update()    
