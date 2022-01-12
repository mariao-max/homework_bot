import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv
from telegram import Bot


load_dotenv()


TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')


class TheAnswerIsNot200Error(Exception):
    """Ответ сервера не равен 200."""


class EmptyDictionaryOrListError(Exception):
    """Пустой словарь или список."""


class RequestExceptionError(Exception):
    """Ошибка запроса."""


class NoDocumentedStatusError(Exception):
    """Недокументированный статус"""

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}



HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s'
)
logger = logging.getLogger(__name__)
logger.addHandler(
    logging.StreamHandler()
)

def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical("Переменные окружения заданы некорректно или отсутсвуют")
        exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    tmp_status = 'reviewing'
    errors = True
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework and tmp_status != homework['status']:
                message = parse_status(homework)
                send_message(bot, message)
                tmp_status = homework['status']
            logger.info(
                'Изменений нет, повторная проверка будет через 10 минут')
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в программе: {error}'
            if errors:
                errors = False
                send_message(bot, message)
            logger.critical(message)
            time.sleep(RETRY_TIME)


def check_tokens():
    """Проверка наличия токенов."""
    token_message = (
     'Отсутствует обязательная переменная окружения: ')
    tokens_bool = True
    if PRACTICUM_TOKEN is None:
        tokens_bool = False
        logger.critical(
            f'{token_message} PRACTICUM_TOKEN')
    if TELEGRAM_TOKEN is None:
        tokens_bool = False
        logger.critical(
            f'{token_message} TELEGRAM_TOKEN')
    if TELEGRAM_CHAT_ID is None:
        tokens_bool = False
        logger.critical(
            f'{token_message} TELEGRAM_CHAT_ID')
    return tokens_bool

def get_api_answer(current_timestamp):
    """Запрос к эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers = HEADERS, params=params)
        if response.status_code != 200:
            code_message = f'{ENDPOINT} недоступен. Код ответа {response.status_code}'
            logger.error(code_message)
            raise TheAnswerIsNot200Error(code_message)
        return response.json()
    except RequestExceptionError as error:
        request_error_message = f'Ошибка запроса({error}) страницы {ENDPOINT}'
        logger.error(request_error_message)
        raise RequestExceptionError(request_error_message)

def check_response(response):
    """Проверка ответа API"""
    homeworks = response['homeworks']
    if homeworks is None:
        check_message = (
        'Ошибка ключа "homeworks" или response'
        'имеет неправильное значение.')
        logger.error(check_message)
        raise  EmptyDictionaryOrListError(check_message)
    if homeworks == []:
        return {}
    if not isinstance(homeworks, list):
        api_message = 'API ответ не является списком'
        logger.error(api_message)
        raise EmptyDictionaryOrListError(api_message)
    return homeworks     


def parse_status(homework):
    """Анализ статуса работы."""
    homework_name = homework['homework_name']
    homework_status = homework.get('status')
    if homework_status is None:
        parse_message = 'Пустое значение "status".'
        raise NoDocumentedStatusError(parse_message)
    if homework_name is None:
        text_error = 'Пустое значение "homework_name".'
        raise NoDocumentedStatusError(parse_message)
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot, message):
    """Отправка сообщения в Телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(
            f'Сообщение в Telegram отправлено: {message}')
    except telegram.TelegramError as telegram_error:
        logger.error(
            f'Сообщение в Telegram не отправлено: {telegram_error}')



if __name__ == '__main__':
    main()

