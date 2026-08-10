"""Backward-compatible API facade for bot handlers."""

from api.admin import (
    admin_change_user_role,
    admin_create_point_type,
    admin_delete_point_type,
    admin_list_point_types,
    admin_list_points,
    admin_list_users,
    admin_list_votes,
    admin_update_point,
    admin_update_point_type,
    admin_upload_point_photo,
)
from api.auth import authenticate_telegram_user, get_telegram_profile
from api.client import close
from api.notifications import acknowledge_notifications, get_pending_notifications
from api.points import (
    create_point,
    get_point,
    list_point_types,
    list_points,
    upload_photo,
    vote,
)

__all__ = [
    "acknowledge_notifications",
    "admin_change_user_role",
    "admin_create_point_type",
    "admin_delete_point_type",
    "admin_list_point_types",
    "admin_list_points",
    "admin_list_users",
    "admin_list_votes",
    "admin_update_point",
    "admin_update_point_type",
    "admin_upload_point_photo",
    "authenticate_telegram_user",
    "close",
    "create_point",
    "get_pending_notifications",
    "get_point",
    "get_telegram_profile",
    "list_point_types",
    "list_points",
    "upload_photo",
    "vote",
]
