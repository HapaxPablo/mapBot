"""Компонент Telegram-бота GeoMap."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def role_label(role: str) -> str:
    """Выполняет операцию компонента Telegram-бота."""
    return {
        "admin": "Администратор",
        "superuser": "Суперпользователь",
        "old_member": "Старый участник",
        "new_member": "Новый участник",
    }.get(role, role)


def admin_user_keyboard(users: list[dict]) -> InlineKeyboardMarkup:
    """Выполняет операцию компонента Telegram-бота."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=(user.get("username") or user.get("first_name") or str(user["telegram_id"]))[:60],
            callback_data=f"admin:user:{user['telegram_id']}",
        )
    ] for user in users])


def admin_type_keyboard(point_types: list[dict], include_add: bool = True) -> InlineKeyboardMarkup:
    """Выполняет операцию компонента Telegram-бота."""
    rows = [[
        InlineKeyboardButton(
            text=f"{point_type['name']} ({'общая карта' if point_type['show_on_main_map'] else 'спец. слой'})"[:64],
            callback_data=f"admin:type:{point_type['id']}",
        )
    ] for point_type in point_types]
    if include_add:
        rows.append([InlineKeyboardButton(text="➕ Добавить тип", callback_data="admin:type-add")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_point_keyboard(points: list[dict]) -> InlineKeyboardMarkup:
    """Выполняет операцию компонента Telegram-бота."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=f"{'✅' if point['is_active'] else '⛔'} {point['title']}"[:64],
            callback_data=f"admin:point:{point['id']}",
        )
    ] for point in points])


def admin_user_roles_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    """Выполняет операцию компонента Telegram-бота."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=label, callback_data=f"admin:user-role:{telegram_id}:{role}")
    ] for role, label in (
        ("admin", "Администратор"),
        ("superuser", "Суперпользователь"),
        ("old_member", "Старый участник"),
        ("new_member", "Новый участник"),
    )])


def admin_type_actions_keyboard(point_type_id: int) -> InlineKeyboardMarkup:
    """Выполняет операцию компонента Telegram-бота."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"admin:type-edit:{point_type_id}")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin:type-delete:{point_type_id}")],
    ])


def admin_type_edit_keyboard(point_type_id: int) -> InlineKeyboardMarkup:
    """Выполняет операцию компонента Telegram-бота."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Название", callback_data=f"admin:type-edit-field:{point_type_id}:name")],
        [InlineKeyboardButton(text="Иконка", callback_data=f"admin:type-edit-field:{point_type_id}:icon_name")],
        [InlineKeyboardButton(text="Показ на общей карте", callback_data=f"admin:type-toggle:{point_type_id}")],
    ])


def admin_point_actions_keyboard(point_id: str) -> InlineKeyboardMarkup:
    """Выполняет операцию компонента Telegram-бота."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"admin:point-edit:{point_id}")],
        [InlineKeyboardButton(text="🔃 Изменить активность", callback_data=f"admin:point-toggle:{point_id}")],
        [InlineKeyboardButton(text="📷 Заменить фото", callback_data=f"admin:point-photo:{point_id}")],
    ])


def admin_point_edit_keyboard(point_id: str) -> InlineKeyboardMarkup:
    """Выполняет операцию компонента Telegram-бота."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Название", callback_data=f"admin:pef:{point_id}:title")],
        [InlineKeyboardButton(text="Описание", callback_data=f"admin:pef:{point_id}:description")],
        [InlineKeyboardButton(text="Тип", callback_data=f"admin:pef:{point_id}:point_type")],
        [InlineKeyboardButton(text="Координаты", callback_data=f"admin:pef:{point_id}:coordinates")],
        [InlineKeyboardButton(text="Доступ пользователей", callback_data=f"admin:pef:{point_id}:allowed_users")],
    ])
