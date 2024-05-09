HOME_DIR = '/home/student/bot_s_gpt'

TOKEN = f'{HOME_DIR}/creds/bot_token.txt'  # token телеграм-бота
IAM_TOKEN = f'{HOME_DIR}/creds/iam_token.txt'
FOLDER_ID = f'{HOME_DIR}/creds/folder_id.txt'

LOGS = f'{HOME_DIR}/logs.txt'  # файл для логов
DB_FILE = f'{HOME_DIR}/messages.db'  # файл для базы данных
SYSTEM_PROMPT = [{'role': 'system', 'text': 'Поддерживай диалог, отвечай на вопросы. Не объясняй пользователю, что ты умеешь и можешь.'}]  # список с системным промтом

MAX_USERS = 3  # максимальное кол-во пользователей
MAX_GPT_TOKENS = 25  # максимальное кол-во токенов в ответе GPT
COUNT_LAST_MSG = 3  # кол-во последних сообщений из диалога

# лимиты для пользователя
MAX_USER_STT_BLOCKS = 5  # аудиоблоков на пользователя
MAX_USER_TTS_SYMBOLS = 500  # символов на пользователя
MAX_USER_GPT_TOKENS = 300 # токенов на пользователя
MAX_TTS_SYMBOLS = 100 # символов на запрос
