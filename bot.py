import telebot
import logging
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from validators import *
from yandex_gpt import ask_gpt
from config import  COUNT_LAST_MSG, LOGS
from creds import get_bot_token
from database import *
from speechkit import *

# настраиваем запись логов в файл
logging.basicConfig(filename=LOGS, level=logging.ERROR, format="%(asctime)s FILE: %(filename)s IN: %(funcName)s MESSAGE: %(message)s", filemode="w")
bot = telebot.TeleBot(get_bot_token())  # создаём объект бота


# обрабатываем команду /start
@bot.message_handler(commands=['start'])
def start_command(message):
    logging.info("Отправка приветственного сообщения")
    user_name = message.from_user.first_name
    bot.send_message(message.chat.id, text = f'''Приветствую, {user_name}! Отправь мне голосовое сообщение или текст, и я отвечу на заданный вопрос.''')

# обрабатываем команду /help
@bot.message_handler(commands=["help"])
def say_help(message):
    logging.info("Отправка информации о командах")
    bot.send_message(message.chat.id, '''Доступные команды:
/start - для начала взаимодействия с ботом и краткого описания его функционала.
/help - для получения информации о доступных командах.
/stt - Преобразование голосового сообщения в текст.
/tts - Преобразование текста в голосовое сообщение.                                                            
/debug - для получения файла с логами.''')

# обрабатываем команду /debug - отправляем файл с логами
@bot.message_handler(commands=['debug'])
def debug(message):
    with open("logs.txt", "rb") as f:
        bot.send_document(message.chat.id, f)

create_database()

# Преобразование голосового сообщения в текст
@bot.message_handler(commands=['stt'])
def stt_handler(message):
    user_id = message.from_user.id
    bot.send_message(user_id, 'Отправь голосовое сообщение, чтобы я его распознал!')
    bot.register_next_step_handler(message, stt)

def stt(message):
    user_id = message.from_user.id
    
    # Проверка, что сообщение действительно голосовое
    if not message.voice:
        return

    # Считаем аудиоблоки и проверяем сумму потраченных аудиоблоков
    stt_blocks = is_stt_block_limit(user_id, message.voice.duration)
    if not stt_blocks:
        return

    file_id = message.voice.file_id  # получаем id голосового сообщения
    file_info = bot.get_file(file_id)  # получаем информацию о голосовом сообщении
    file = bot.download_file(file_info.file_path)  # скачиваем голосовое сообщение

    # Получаем статус и содержимое ответа от SpeechKit
    status, text = speech_to_text(file)  # преобразовываем голосовое сообщение в текст

    # Если статус True - отправляем текст сообщения и сохраняем в БД, иначе - сообщение об ошибке
    if status:
        # Записываем сообщение и кол-во аудиоблоков в БД
        add_message(user_id=user_id, full_message=[text, 'user', 0, 0, stt_blocks[0]])
        bot.send_message(user_id, text, reply_to_message_id=message.id)
    else:
        bot.send_message(user_id, text)

def is_stt_block_limit(user_id, duration):  
    # Переводим секунды в аудиоблоки  
    audio_blocks = math.ceil(duration / 15) # округляем в большую сторону  
    
    # Функция из БД для подсчёта всех потраченных пользователем аудиоблоков  
    all_block = count_all_limits(user_id, audio_blocks)  
    
    # Проверяем, что аудио длится меньше 30 секунд  
    if duration >= 30:  
        msg = "SpeechKit STT работает с голосовыми сообщениями меньше 30 секунд"  
        return None, msg

    # Сравниваем all_blocks с количеством доступных пользователю аудиоблоков  
    if all_block >= MAX_USER_STT_BLOCKS:  
        msg = f"Превышен общий лимит SpeechKit STT {MAX_USER_STT_BLOCKS}. Использовано {all_block} блоков. Доступно: {MAX_USER_STT_BLOCKS - all_block}"  
        return None, msg

    return audio_blocks, None



# Преобразование текста в голос
@bot.message_handler(commands=['tts'])
def tts_handler(message):
        user_id = message.from_user.id
        bot.send_message(user_id, 'Отправь следующим сообщеним текст, чтобы я его озвучил!')
        bot.register_next_step_handler(message, tts)

def tts(message):
    user_id = message.from_user.id
    text = message.text

    # Проверка, что сообщение действительно текстовое
    if message.content_type != 'text':
        bot.send_message(user_id, 'Отправь текстовое сообщение')
        return

    # Считаем символы в тексте и проверяем сумму потраченных символов
    tts_symbols = is_tts_symbol_limit(user_id, text)
    if tts_symbols is None:
        return

    # Записываем сообщение и кол-во символов в БД
    
    add_message(user_id=user_id, full_message=[text, 'user', 0, tts_symbols[0], 0])

    # Получаем статус и содержимое ответа от SpeechKit
    status, content = text_to_speech(text)

    # Если статус True - отправляем голосовое сообщение, иначе - сообщение об ошибке
    if status:
        bot.send_voice(user_id, content)
    else:
        bot.send_message(user_id, content)

# лимит символов в запросе
def is_tts_symbol_limit(user_id, answer_gpt): 

    text_symbols = len(answer_gpt) 
    print(10) 
    # Функция из БД для подсчёта всех потраченных пользователем символов 
    all_symbols = count_all_limits(user_id, text_symbols) 
     
    # Сравниваем all_symbols с количеством доступных пользователю символов 
    if all_symbols >= MAX_USER_TTS_SYMBOLS: 
        msg = f"Превышен общий лимит SpeechKit TTS {MAX_USER_TTS_SYMBOLS}. Использовано: {all_symbols} символов. Доступно: {MAX_USER_TTS_SYMBOLS - all_symbols}" 
        bot.send_message(user_id, msg) 
        return None
 
    # Сравниваем количество символов в тексте с максимальным количеством символов в тексте 
    if text_symbols >= MAX_TTS_SYMBOLS: 
        msg = f"Превышен лимит SpeechKit TTS на запрос {MAX_TTS_SYMBOLS}, в сообщении {text_symbols} символов" 
        bot.send_message(user_id, msg) 
        return None
    return len(answer_gpt), None



# Декоратор для обработки голосовых сообщений, полученных ботом
# Декоратор для обработки голосовых сообщений, полученных ботом
@bot.message_handler(content_types=['voice'])
def handle_voice(message: telebot.types.Message):
    try:
        user_id = message.from_user.id
        
        # Проверка на максимальное количество пользователей
        status_check_users, error_message = check_number_of_users(user_id)
        print(0)
        if not status_check_users:
            bot.send_message(user_id, error_message)
            return
        duration = message.voice.duration
        # Проверка на доступность аудиоблоков
        print(0)
        stt_blocks, error_message = is_stt_block_limit(user_id, duration)
        print(0)
        if error_message:
            bot.send_message(user_id, error_message)
            return

        # Обработка голосового сообщения
        file_id = message.voice.file_id
        file_info = bot.get_file(file_id)
        file = bot.download_file(file_info.file_path)
        status_stt, stt_text = speech_to_text(file)
        if not status_stt:
            bot.send_message(user_id, stt_text)
            return
        print(0)
        # Запись в БД
        add_message(user_id=user_id, full_message=[stt_text, 'user', 0, 0, stt_blocks])
        print(0)
        # Проверка на доступность GPT-токенов
        last_messages, total_spent_tokens = select_n_last_messages(user_id, COUNT_LAST_MSG)
        total_gpt_tokens, error_message = is_gpt_token_limit(last_messages, total_spent_tokens)
        if error_message:
            bot.send_message(user_id, error_message)
            return
        print(0)
        # Запрос к GPT и обработка ответа
        status_gpt, answer_gpt, tokens_in_answer = ask_gpt(last_messages)
        if not status_gpt:
            bot.send_message(user_id, answer_gpt)
            return
        total_gpt_tokens += tokens_in_answer
        print(1)
        # Проверка на лимит символов для SpeechKit
        tts_symbols, error_message = is_tts_symbol_limit(user_id, answer_gpt)
        print(2)
        # Запись ответа GPT в БД
        add_message(user_id=user_id, full_message=[answer_gpt, 'assistant', total_gpt_tokens, tts_symbols, 0])
        
        if error_message:
            bot.send_message(user_id, error_message)
            return
        print(3)
        # Преобразование ответа в аудио и отправка
        status_tts, voice_response = text_to_speech(answer_gpt)
        if status_tts:
            bot.send_voice(user_id, voice_response, reply_to_message_id=message.id)
        else:
            bot.send_message(user_id, answer_gpt, reply_to_message_id=message.id)
    except Exception as e:
        logging.error(e)
        bot.send_message(user_id, "Не получилось ответить. Попробуй записать другое сообщение")




# обрабатываем текстовые сообщения
@bot.message_handler(content_types=['text'])
def handle_text(message):
    try:
        user_id = message.from_user.id

        # ВАЛИДАЦИЯ: проверяем, есть ли место для ещё одного пользователя (если пользователь новый)
        status_check_users, error_message = check_number_of_users(user_id)
        if not status_check_users:
            bot.send_message(user_id, error_message)  # мест нет =(
            return
            
        # БД: добавляем сообщение пользователя и его роль в базу данных
        full_user_message = [message.text, 'user', 0, 0, 0]
        add_message(user_id=user_id, full_message=full_user_message)
        
        # ВАЛИДАЦИЯ: считаем количество доступных пользователю GPT-токенов
        # получаем последние 4 (COUNT_LAST_MSG) сообщения и количество уже потраченных токенов
        last_messages, total_spent_tokens = select_n_last_messages(user_id, COUNT_LAST_MSG)
        # получаем сумму уже потраченных токенов + токенов в новом сообщении и оставшиеся лимиты пользователя
        total_gpt_tokens, error_message = is_gpt_token_limit(last_messages, total_spent_tokens)
        if error_message:
                # если что-то пошло не так — уведомляем пользователя и прекращаем выполнение функции
            bot.send_message(user_id, error_message)
            return
        
        # GPT: отправляем запрос к GPT
        status_gpt, answer_gpt, tokens_in_answer = ask_gpt(last_messages)
        # GPT: обрабатываем ответ от GPT
        if not status_gpt:
                # если что-то пошло не так — уведомляем пользователя и прекращаем выполнение функции
            bot.send_message(user_id, answer_gpt)
            return
        # сумма всех потраченных токенов + токены в ответе GPT
        total_gpt_tokens += tokens_in_answer

        # БД: добавляем ответ GPT и потраченные токены в базу данных
        full_gpt_message = [answer_gpt, 'assistant', total_gpt_tokens, 0, 0]
        add_message(user_id=user_id, full_message=full_gpt_message)
        
        bot.send_message(user_id, answer_gpt, reply_to_message_id=message.id)  # отвечаем пользователю
    except Exception as e:
        logging.error(e)  # если ошибка - записываем её в логи
        bot.send_message(message.from_user.id, "Ошибка! Попробуйте другое сообщение.")


# обрабатываем все остальные типы сообщений
@bot.message_handler(func=lambda: True)
def handler(message):
    bot.send_message(message.from_user.id, "Отправлять можно только голосовое или текстовое сообщение!")



# создание кнопок №№№
def create_keyboard(options):
    buttons = (KeyboardButton(text=option) for option in options)
    keyboard = ReplyKeyboardMarkup(
        row_width=2,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    keyboard.add(*buttons)
    return keyboard


bot.polling()