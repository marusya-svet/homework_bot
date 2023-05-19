import logging
import os
import sys
import time

import requests
import telegram.error

from dotenv import load_dotenv
from telegram import Bot
from logging import StreamHandler

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='w',
    format='%(asctime)s, %(levelname)s, %(message)s'
)
logger = logging.getLogger(__name__)
handler = StreamHandler(sys.stdout)
logger.addHandler(handler)


def check_tokens():
    """Проверка доступности токенов."""
    return all((PRACTICUM_TOKEN,
                TELEGRAM_CHAT_ID, TELEGRAM_TOKEN))


def send_message(bot, message):
    """Отправка сообщений в Telegram-чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение отправлено!')
    except telegram.error.TelegramError as error:
        logging.error(f'Сообщение не было отправлено: {error}')


def get_api_answer(timestamp):
    """Запрос к API."""
    try:
        params = {'from_date': timestamp}
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != 200:
            raise AssertionError('Ошибка доступности адреса')
    except requests.RequestException as error:
        logging.error(f'Ошибка запроса: {error}')
    return response.json()


def check_response(response):
    """Проверк аответа API на соответсвие документации."""
    if not isinstance(response, dict):
        print(response)
        raise TypeError('Ответ не является словарем')
    hw = response.get('homeworks')
    if hw is None:
        raise KeyError('Ответ не содержит ключ homeworks')
    if not isinstance(hw, list):
        raise TypeError('HW не является списком')


def parse_status(homework):
    """Извлекает статус конкретной hw."""
    try:
        status = homework['status']
        if status not in HOMEWORK_VERDICTS:
            logging.error('Недокументированный статус hw')
        homework_name = homework['homework_name']
        verdict = HOMEWORK_VERDICTS[status]
    except KeyError as error:
        raise KeyError(f'Отсутствует название hw: {error}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Отсутствуют переменные окружения')
        sys.exit()
    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    from_date = timestamp - RETRY_PERIOD
    while True:
        try:
            response = get_api_answer(from_date)
            check_response(response)
            homeworks = response['homeworks']
            if homeworks:
                hw = homeworks[0]
                old_status = hw['status']
                new_status = parse_status(hw)
                if old_status != new_status:
                    send_message(bot, new_status)
            else:
                logging.debug('Статус работы еще не изменился')
            from_date = response['current_date']
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
