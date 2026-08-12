"""Компонент Telegram-бота GeoMap."""

def api_error_text(exc: Exception, fallback: str) -> str:
    """Выполняет операцию компонента Telegram-бота."""
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            detail = response.json().get("detail")
            if detail:
                return str(detail)
        except (ValueError, AttributeError):
            pass
    return fallback
