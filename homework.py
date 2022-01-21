import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv
from json.decoder import JSONDecodeError

from exceptions import (NoDocumentedStatusError, EmptyDictionaryOrListError,
                        RequestExceptionError, TheAnswerIsNot200Error,
                        ResponseIsNone)

load_dotenv()


TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')

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

LAST_MESSAGE = ''


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while check_tokens():
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework[0])
                if message != LAST_MESSAGE:
                    send_message(bot, message)
                    logger.info('Сообщение отправлено')
            else:
                logger.info('Изменений нет, повторная проверка'
                            'будет через 10 минут')
                time.sleep(RETRY_TIME)
            current_timestamp = response['current_date']
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в программе: {error}'
            logger.error(message)
            send_message(bot, message)
    else:
        logger.critical('Переменные окружения заданы'
                        'некорректно или отсутсвуют')


def check_tokens():
    """Проверка наличия токенов."""
    tokens = [TELEGRAM_CHAT_ID, PRACTICUM_TOKEN, TELEGRAM_TOKEN]
    for token in tokens:
        if token is None:
            return False
        return True


def get_api_answer(current_timestamp):
    """Запрос к эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != 200:
            code_message = f'{ENDPOINT} недоступен.'
            logger.error(code_message)
            raise TheAnswerIsNot200Error(code_message)
        response = response.json()
        return response
    except JSONDecodeError as value_error:
        code_msg = f'Код ответа API: {value_error}'
        logger.error(code_msg)
        raise JSONDecodeError(code_msg)
    except RequestExceptionError as error:
        request_error_message = f'Ошибка запроса({error}) страницы {ENDPOINT}'
        logger.error(request_error_message)
        raise RequestExceptionError(request_error_message)


def check_response(response):
    """Проверка ответа API."""
    if response is None:
        response_message = 'Ответ пуст'
        logger.error(response_message)
        raise ResponseIsNone(response_message)
    if not isinstance(response, dict):
        type_message = 'Некорректный тип данных на входе'
        logger.error(type_message)
        raise TypeError(type_message)
    if 'homeworks' not in response:
        key_message = 'По ключу "homeworks" нет информации'
        logger.error(key_message)
        raise KeyError(key_message)
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        type_message = 'Данные по ключу homeworks не являются списком'
        logger.error(type_message)
        raise TypeError(type_message)
    if not homeworks:
        check_message = ('Список работ пуст')
        logger.error(check_message)
        raise EmptyDictionaryOrListError(check_message)
    return homeworks


def parse_status(homework):
    """Анализ статуса работы."""
    if not isinstance(homework, dict):
        message = 'Некорректный тип данных.'
        logger.error(message)
        raise TypeError(message)
    if 'homework_name' not in homework:
        parse_message = 'Нет ключа "homework_name".'
        raise KeyError(parse_message)
    if 'status' not in homework:
        parse_message = 'Нет ключа "status".'
        raise KeyError(parse_message)
    if homework['status'] not in HOMEWORK_STATUSES:
        message = "Неожиданный статус."
        logger.error(message)
        raise NoDocumentedStatusError(message)
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot, message):
    """Отправка сообщения в Телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.TelegramError as telegram_error:
        logger.error(
            f'Сообщение в Telegram не отправлено: {telegram_error}')


if __name__ == '__main__':
    main()
