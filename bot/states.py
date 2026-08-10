from aiogram.fsm.state import State, StatesGroup


class AddPoint(StatesGroup):
    point_type = State()
    title = State()
    description = State()
    location = State()
    photo = State()


class PointsList(StatesGroup):
    scope = State()


class Admin(StatesGroup):
    menu = State()
    users = State()
    type_name = State()
    type_icon = State()
    type_visibility = State()
    type_edit_value = State()
    points = State()
    point_edit_value = State()
    point_photo = State()
