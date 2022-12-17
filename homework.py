import os
import sys
from http import HTTPStatus

import logging
import requests
import telegram
import time

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    filename="error.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(filename)s - %(message)s",
)

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


def main():
    """Основная логика работы бота."""
    logging.info('Бот запущен')
    if not check_tokens():
        msg = 'Отсутствует одна или несколько переменных окружения'
        logging.critical(msg)
        sys.exit(msg)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            logging.info('Список работ получен')
            if len(homeworks) > 0:
                send_message(bot, parse_status(homeworks[0]))
                timestamp = response['current_date']
            else:
                logging.info('Новых заданий нет')
        except Exception as error:
            message = f'Ошибка: {error}'
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отсылаем сообщение."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception:
        logging.error('Ошибка при отправке сообщения')
    else:
        logging.debug('Сообщение успешно отправлено')


def get_api_answer(timestamp):
    """Делаем запрос на сервер ЯП."""
    global response
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            response.raise_for_status()
        logging.info('Ответ на запрос к API: 200 OK')
        return response.json()
    except requests.RequestException:
        message = f'Ошибка при запросе к API: {response.status_code}'
        raise requests.RequestException(message)


def check_response(response):
    """Проверяем ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError()
    if 'homeworks' not in response:
        raise KeyError()
    if not isinstance(response.get('homeworks'), list):
        raise TypeError()
    else:
        return response.get('homeworks')


def parse_status(homework):
    """Проверка статуса домашней работы."""
    if not isinstance(homework, dict):
        raise KeyError()
    if 'status' not in homework:
        raise KeyError()
    if 'homework_name' not in homework:
        raise KeyError()
    if not isinstance(homework.get('status'), str):
        raise TypeError()
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status in HOMEWORK_VERDICTS:
        verdict = HOMEWORK_VERDICTS.get(homework_status)
        return ('Изменился статус проверки работы '
                f'"{homework_name}". {verdict}')
    else:
        raise Exception('Неизвестный статус работы')


if __name__ == '__main__':
    main()
