from http import HTTPStatus
import sys
import time
import telegram
import requests
import os
from dotenv import load_dotenv
import logging
from exceptions import (HomeworkStatusesException, SendMessageException,
                        ApiAnswerException)

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

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


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        logging.debug('Начало отправки сообщения')
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
    except Exception:
        raise SendMessageException('Сбой при отправке сообщения: {Exception}')
    else:
        logging.debug('Удачная отправка сообщения')


def get_api_answer(timestamp):
    """Возвращает ответ API приведенный к типу данных python."""
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
    except Exception:
        raise ApiAnswerException('Сбой при отправке сообщения: {Exception}')
    else:
        if homework_statuses.status_code == HTTPStatus.OK:
            return homework_statuses.json()
        message = 'Сервис недоступен.'
        raise Exception(message)


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    try:
        homeworks = response['homeworks']
    except KeyError as error:
        raise KeyError(f'В словаре нет запрашиваемого ключа {error}')
    if isinstance(homeworks, list):
        return homeworks
    raise TypeError('Под ключем "homeworks" ожидается список')


def parse_status(homework):
    """Извлекает статус домашней работы."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if (homework_name is None) or (status is None):
        raise KeyError('В словаре нет запрашиваемого ключа')
    if status in HOMEWORK_VERDICTS:
        verdict = HOMEWORK_VERDICTS[status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    message = 'Статус домашней работы не соответсвутет ожидаемому.'
    raise HomeworkStatusesException(message)


def main():
    """Основная логика работы бота."""
    tokens = check_tokens()
    if not tokens:
        logging.critical(f'Ошибка доступа к переменным окружения: {Exception}')
        sys.exit('Ошибка переменных окружения. Работа программы прервана')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0
    status_homework = []

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homework_list = check_response(response)
            if status_homework != homework_list[0]:
                status_homework = homework_list[0]
                message = parse_status(status_homework)
                send_message(bot, message)
        except ApiAnswerException:
            logging.error(f'Ошибка при запросе к основному API: {Exception}')
        except SendMessageException:
            logging.error(f'Сбой при отправке сообщения: {Exception}')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
