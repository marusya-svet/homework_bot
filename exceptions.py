import telegram


class CustomTelegramError(telegram.error.TelegramError):
    """Ошибка тг"""
