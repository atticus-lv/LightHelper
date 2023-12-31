import bpy
from bpy.app.translations import pgettext_iface as p_

from .utils import get_all_light_effect_items_state, get_linking_coll
from .utils import CollectionType, StateValue, SAFE_OBJ_NAME
from .utils import get_lights_from_effect_obj

select_op_id = 'llp.select_item'
toggle_op_id = 'llp.toggle_light_linking'
add_op_id = 'llp.add_light_linking'
remove_op_id = 'llp.remove_light_linking'
link_op_id = 'llp.link_selected_objs'
question_op_id = 'llp.question'


def get_light_icon(light):
    data = light.data
    type_icon = {
        'AREA': 'LIGHT_AREA',
        'POINT': 'LIGHT_POINT',
        'SPOT': 'LIGHT_SPOT',
        'SUN': 'LIGHT_SUN',
    }
    if hasattr(data, 'type'):
        return type_icon.get(data.type, 'OBJECT_DATA')

    return 'OBJECT_DATA'


def get_item_icon(item: bpy.types.Object | bpy.types.Collection):
    if isinstance(item, bpy.types.Object):
        return 'OBJECT_DATA'
    elif isinstance(item, bpy.types.Collection):
        return 'OUTLINER_COLLECTION'
    else:
        return 'QUESTION'


def draw_select_btn(layout, item):
    op = layout.operator(select_op_id, text=item.name, icon=get_item_icon(item), emboss=False)
    if isinstance(item, bpy.types.Object):
        op.obj = item.name
    else:
        op.coll = item.name


def draw_toggle_btn(layout,
                    state_info: dict,
                    light_obj: bpy.types.Object,
                    item: bpy.types.Object | bpy.types.Collection):
    """Draw toggle button for receiver / blocker collection"""
    if receive_value := state_info.get(CollectionType.RECEIVER):  # exist in receiver collection
        icon = 'OUTLINER_OB_LIGHT' if receive_value == StateValue.INCLUDE else 'OUTLINER_DATA_LIGHT'
        # text = 'Include' if receive_value == StateValue.INCLUDE else 'Exclude'
        toggle = True if receive_value == StateValue.INCLUDE else False
        sub = layout.row(align=True)
        sub.alert = toggle
        op = sub.operator(toggle_op_id, text='', icon=icon)
        op.coll_type = CollectionType.RECEIVER.value
        op.light = light_obj.name
        if isinstance(item, bpy.types.Object):
            op.obj = item.name
        else:
            op.coll = item.name

    if block_value := state_info.get(CollectionType.BLOCKER):  # exist in exclude collection
        icon = 'SHADING_SOLID' if block_value == StateValue.INCLUDE else 'SHADING_RENDERED'
        # text = 'Include' if block_value == StateValue.INCLUDE else 'Exclude'
        toggle = True if block_value == StateValue.INCLUDE else False
        sub = layout.row(align=True)
        sub.alert = toggle
        op = sub.operator(toggle_op_id, text='', icon=icon)
        op.coll_type = CollectionType.BLOCKER.value
        op.light = light_obj.name
        if isinstance(item, bpy.types.Object):
            op.obj = item.name
        else:
            op.coll = item.name


def draw_remove_button(layout,
                       light_obj: bpy.types.Object,
                       item: bpy.types.Object | bpy.types.Collection):
    op = layout.operator(remove_op_id, text='', icon="X")
    if isinstance(item, bpy.types.Object):
        op.obj = item.name
    else:
        op.coll = item.name
    op.light = light_obj.name
    op.remove_all = True


def draw_light_link(object, layout, use_pin=False):
    if object is None: return

    col = layout.column()
    light_linking = object.light_linking

    row = col.row(align=True)

    row.label(text=object.name, icon='LIGHT')
    if use_pin:
        row.prop(bpy.context.scene, 'light_linking_pin', text='', icon='PINNED')

    # col.prop(light_linking, 'receiver_collection', text='')

    if not light_linking.receiver_collection:
        col.operator('object.light_linking_receiver_collection_new', text='', icon='ADD')
        return

    row = col.row(align=True)
    row.prop(object, 'light_linking_state', expand=True)
    row.prop(bpy.context.scene, 'force_light_linking_state', icon='FILE_REFRESH', toggle=True, text='')

    if not object.show_light_linking_collection: return

    col.separator()

    row = col.row(align=True)
    row.template_light_linking_collection(row, light_linking, "receiver_collection")
    row.operator('object.light_linking_unlink_from_collection', text='', icon='REMOVE')


class LLT_PT_light_control_panel(bpy.types.Panel):
    bl_label = ""
    bl_idname = "LLT_PT_light_control_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "LH"
    bl_options = {'HEADER_LAYOUT_EXPAND'}

    @classmethod
    def poll(cls, context):
        return context.scene.render.engine == 'CYCLES'

    def draw_header(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.label(text="Light Linking")
        tips = row.operator(question_op_id, text='', icon='QUESTION', emboss=False)
        tips.data = p_(
            """Light Linking Panel
This Panel Lists all the objects that are affected by the selected/pinned light.
Provides buttons to toggle the light effecting state of the objects."""
        )

        row.separator()

    def draw(self, context):
        layout = self.layout
        self.draw_light_objs_control(context, layout)

    # def draw_light(self, context, layout):
    #     if context.scene.light_linking_pin:
    #         obj = context.scene.light_linking_pin_object
    #         if not obj: return
    #         draw_light_link(obj, layout, use_pin=True)
    #     else:
    #         if not context.object:
    #             layout.label(text="No object selected")
    #         elif context.object.type != 'LIGHT':
    #             layout.label(text="Selected object is not a light")
    #             layout.operator('object.light_linking_receiver_collection_new', text='As light', icon='ADD')
    #             return
    #
    #         draw_light_link(context.object, layout, use_pin=True)
    #

    def draw_light_objs_control(self, context, layout):
        if context.scene.light_linking_pin:
            light_obj = context.scene.light_linking_pin_object
        else:
            light_obj = context.object
        if not light_obj: return

        col = layout.column()
        # top line
        row = col.row(align=True)
        row.label(text=f"{light_obj.name}", icon=get_light_icon(light_obj))
        row.separator()
        row.prop(bpy.context.scene, 'light_linking_pin', text='', icon='PINNED')

        coll_receiver = get_linking_coll(light_obj, CollectionType.RECEIVER)
        coll_blocker = get_linking_coll(light_obj, CollectionType.BLOCKER)

        # return if no receiver/blocker collection (exclude the safe obj)
        if (not coll_receiver and not coll_blocker) or (
                SAFE_OBJ_NAME not in coll_receiver.objects) or (
                SAFE_OBJ_NAME not in coll_blocker.objects):
            op = col.operator(add_op_id, text='Init', icon='ADD')
            op.init = True
            op.light = light_obj.name
            return

        obj_state_dict = get_all_light_effect_items_state(light_obj)

        safe_obj = bpy.data.objects.get(SAFE_OBJ_NAME)
        if len(obj_state_dict) == 1 and safe_obj in obj_state_dict.keys():
            box = col.box()
            row = box.row()
            row.label(text='', icon='ADD')
            row.prop(context.window_manager, 'light_linking_add_collection', text='', icon='OUTLINER_COLLECTION')
            row.prop(context.window_manager, 'light_linking_add_object', text='', icon='OBJECT_DATA')

            row = box.row()
            op = row.operator(link_op_id, icon='ADD')
            op.light = light_obj.name
            return

        col.separator()

        for (item, state_info) in obj_state_dict.items():
            if item.name == SAFE_OBJ_NAME: continue  # skip safe obj
            row = col.row(align=False)
            row.scale_x = 1.1
            row.scale_y = 1.1

            draw_select_btn(row, item)
            draw_toggle_btn(row, state_info, light_obj, item)
            row.separator()
            draw_remove_button(row, light_obj, item)

        # extra op
        col.separator()
        box = col.box()
        row = box.row()
        row.label(text='', icon='ADD')
        row.prop(context.window_manager, 'light_linking_add_collection', text='', icon='OUTLINER_COLLECTION')
        row.prop(context.window_manager, 'light_linking_add_object', text='', icon='OBJECT_DATA')

        row = box.row()
        op = row.operator(link_op_id, icon='ADD')
        op.light = light_obj.name


class LLT_PT_obj_control_panel(bpy.types.Panel):
    bl_label = ""
    bl_idname = "LLT_PT_obj_control_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "LH"
    bl_options = {'HEADER_LAYOUT_EXPAND'}

    @classmethod
    def poll(cls, context):
        return context.scene.render.engine == 'CYCLES'

    def draw_header(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.label(text="Object Linking")
        tips = row.operator(question_op_id, text='', icon='QUESTION', emboss=False)
        tips.data = p_(
            """Object Linking Panel
This Panel Lists all the lights that affected the selected/pinned object.
Provides buttons to toggle the light effecting state of the objects."""
        )
        row.separator()

    def draw(self, context):
        layout = self.layout
        self.draw_object(context, layout)

    def draw_object(self, context, layout):
        if context.scene.object_linking_pin:
            item = context.scene.object_linking_pin_object
        else:
            item = context.object
        if not item: return
        if item.type == 'LIGHT':
            layout.label(text="Light can't be an effected object")
            return

        col = layout.column()
        # top line
        row = col.row(align=True)
        row.label(text=f"{item.name}", icon=get_light_icon(item))
        row.separator()
        row.prop(bpy.context.scene, 'object_linking_pin', text='', icon='PINNED')

        col.separator()

        obj_state_dict = get_lights_from_effect_obj(item)
        if len(obj_state_dict) == 0:
            col.label(text='No light effecting this object', icon='LIGHT')
            box = col.box()
            box.prop(context.window_manager, 'object_linking_add_object', text='', icon='ADD')
            return
        for (light_obj, state_info) in obj_state_dict.items():
            row = col.row()
            draw_select_btn(row, light_obj)
            draw_toggle_btn(row, state_info, light_obj, item)
            row.separator()
            draw_remove_button(row, light_obj, item)

        box = col.box()
        box.prop(context.window_manager, 'object_linking_add_object', text='', icon='ADD')


def update_pin_object(self, context):
    """Update pin object, effect the context layout object"""
    if context.scene.light_linking_pin is True:
        if context.object and context.object.select_get():
            context.scene.light_linking_pin_object = context.object
        else:
            context.scene.light_linking_pin = False
    else:
        context.scene.light_linking_pin_object = None


def update_pin_object2(self, context):
    """Update pin object, effect the context layout object"""
    if context.scene.object_linking_pin is True:
        if context.object and context.object.select_get():
            context.scene.object_linking_pin_object = context.object
        else:
            context.scene.object_linking_pin = False
    else:
        context.scene.object_linking_pin_object = None


def update_add_collection(self, context):
    """Add collection to light's receiver and blocker collection
    Most of the time, use drag and drop in the property layout to add
    """
    wm = context.window_manager
    if wm.light_linking_add_collection is None: return

    if context.scene.light_linking_pin:
        obj = context.scene.light_linking_pin_object
    else:
        obj = context.object
    if obj is None:
        wm.light_linking_add_collection = None
        return

    coll = wm.light_linking_add_collection
    # add collection to light's receiver and blocker collection
    if coll.name not in obj.light_linking.receiver_collection.children:
        obj.light_linking.receiver_collection.children.link(coll)
    if coll.name not in obj.light_linking.blocker_collection.children:
        obj.light_linking.blocker_collection.children.link(coll)
    # restore
    wm.light_linking_add_collection = None


def update_add_obj(self, context):
    """Add object to light's receiver and blocker collection
    Most of the time, use drag and drop in the property layout to add
    """
    wm = context.window_manager
    if wm.light_linking_add_object is None: return

    if context.scene.light_linking_pin:
        obj = context.scene.light_linking_pin_object
    else:
        obj = context.object
    if obj is None:
        wm.light_linking_add_object = None
        return

    obj2 = wm.light_linking_add_object
    # add collection to light's receiver and blocker collection
    if obj2.name not in obj.light_linking.receiver_collection.objects:
        obj.light_linking.receiver_collection.objects.link(obj2)
    if obj2.name not in obj.light_linking.blocker_collection.objects:
        obj.light_linking.blocker_collection.objects.link(obj2)
    # restore
    wm.light_linking_add_object = None


def update_add_light(self, context):
    wm = context.window_manager
    if wm.object_linking_add_object is None: return

    if context.scene.object_linking_pin:
        obj = context.scene.object_linking_pin_object
    else:
        obj = context.object
    if obj is None or obj == wm.object_linking_add_object:
        wm.object_linking_add_object = None
        return

    light = wm.object_linking_add_object

    init_op = getattr(getattr(bpy.ops, add_op_id.split('.')[0]), add_op_id.split('.')[1])
    init_op('INVOKE_DEFAULT', light=light.name, init=True, obj=obj.name)

    coll1 = light.light_linking.receiver_collection
    coll2 = light.light_linking.blocker_collection

    if coll1 and obj.name not in coll1.objects:
        coll1.objects.link(obj)
    if coll2 and obj.name not in coll2.objects:
        coll2.objects.link(obj)

    # restore
    wm.object_linking_add_object = None

def register():
    # pin object, use to change context layout object
    bpy.types.Scene.light_linking_pin_object = bpy.props.PointerProperty(
        poll=lambda self, obj: obj.type in {'LIGHT', 'MESH'}, type=bpy.types.Object,
    )
    bpy.types.Scene.object_linking_pin_object = bpy.props.PointerProperty(
        poll=lambda self, obj: obj.type in {'MESH'}, type=bpy.types.Object,
    )
    # pin property to change context draw layout
    bpy.types.Scene.light_linking_pin = bpy.props.BoolProperty(name='Pin', update=update_pin_object)
    bpy.types.Scene.object_linking_pin = bpy.props.BoolProperty(name='Pin', update=update_pin_object2)

    # drag & drop to add
    bpy.types.WindowManager.light_linking_add_collection = bpy.props.PointerProperty(name='Drag and Drop to Add',
                                                                                     type=bpy.types.Collection,
                                                                                     update=update_add_collection
                                                                                     )
    bpy.types.WindowManager.light_linking_add_object = bpy.props.PointerProperty(name='Drag and Drop to Add',
                                                                                 type=bpy.types.Object,
                                                                                 update=update_add_obj
                                                                                 )
    bpy.types.WindowManager.object_linking_add_object = bpy.props.PointerProperty(name='Drag and Drop to Add',
                                                                                  type=bpy.types.Object,
                                                                                  update=update_add_light
                                                                                  )

    bpy.utils.register_class(LLT_PT_light_control_panel)
    bpy.utils.register_class(LLT_PT_obj_control_panel)


def unregister():
    del bpy.types.Scene.light_linking_pin_object
    del bpy.types.Scene.light_linking_pin
    del bpy.types.Scene.object_linking_pin_object
    del bpy.types.WindowManager.light_linking_add_collection
    del bpy.types.WindowManager.light_linking_add_object
    del bpy.types.WindowManager.object_linking_add_object

    bpy.utils.unregister_class(LLT_PT_light_control_panel)
    bpy.utils.unregister_class(LLT_PT_obj_control_panel)
