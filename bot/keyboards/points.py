from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from runtime import POINTS_BACK_BUTTON, POINTS_COMMON_BUTTON, POINTS_PERSONAL_BUTTON


def point_type_keyboard(point_types: list[dict]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=point_type["name"],
            callback_data=f"add_point_type:{point_type['id']}",
        )
    ] for point_type in point_types])


def points_scope_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=POINTS_PERSONAL_BUTTON), KeyboardButton(text=POINTS_COMMON_BUTTON)],
            [KeyboardButton(text=POINTS_BACK_BUTTON)],
        ],
        resize_keyboard=True,
    )


def point_vote_keyboard(point_id: str, likes: int, dislikes: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"❤️ ({likes})", callback_data=f"vote:like:{point_id}"),
        InlineKeyboardButton(text=f"👎 ({dislikes})", callback_data=f"vote:dislike:{point_id}"),
    ]])
