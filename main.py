import ini
import time
import logging
import telebot
from telebot import types
from video_utils import VideoFromChannel

config = ini.parse(open('config.ini').read())

_logging = telebot.logger

if not config["Telegram"]["DEBUG"]:
    telebot.logger.setLevel(logging.WARNING)
else:
    telebot.logger.setLevel(logging.DEBUG)

bot = telebot.TeleBot(config["Telegram"]["TOKEN"])
vfc_dict = {}
form_dict = {}

INFO_MGS = """1 - Для начала введите сылку на пост с видео, после чего он будет сохранен и поиск начнется
2 - Введите название канала вместе с символом @. Например: @your_channel.
Эта ссылка необходима для отправки видео, то есть нужно указать канал, в который вы хотите отправлять все найденные видео
3 - Укажите глубину для поисковой выборки. По умолчанию она равна 1
4 - После чего нажмите кнопку "Начать поиск"
5 - Бот вам пришлёт все найденные видео, из которых вы можете отправить необходимые по кнопке 'Запостить'"""

class Form:
    def __init__(self):
        self.post_with_video = None
        self.target_channel = None


def get_msg_text(message):
    chat_id = message.chat.id
    text = message.text
    form = form_dict.get(chat_id)
    if not form:
        form_dict[chat_id] = text
        bot.reply_to(message, "Не удалось получить введённые данные.")
    return chat_id, text, form


def get_data_step(message, *args):
    try:
        inst_var, msg = args
        chat_id, text, form = get_msg_text(message)
        setattr(form, inst_var, text)
        if getattr(form, inst_var):
            bot.send_message(chat_id, "Был успешно сохранён %s!" % msg)
        else:
            bot.send_message(chat_id, "ВНИМАНИЕ! Не удалось сохранить %s!" % msg)
    except Exception as ex:
        _logging.error(ex)


def change_depth(message):
    vfc_instance = vfc_dict.get(message.chat.id)
    depth = vfc_instance.change_depth(new_depth=int(message.text))
    bot.reply_to(message, "Глубина поиска изменена на %s!" % depth)


def search_start(message):
    form = form_dict.get(message.chat.id)
    vfc_instance = vfc_dict.get(message.chat.id)
    if vfc_instance and form:
        videos_count = vfc_instance.get_video_from_url(_url=form.post_with_video)
        bot.reply_to(message, "По ссылке было найдено %s видео." % videos_count)
    else:
        bot.reply_to(message, "Неудалось получить данные! Попробуйте снова.")


def print_user_data(message):
    form = form_dict.get(message.chat.id)
    vfc = vfc_dict.get(message.chat.id)
    preview_text = f"1. Ссылка на контент: {form.post_with_video or 'Отсутствует!'}\n" \
                   f"2. Целевой канал для постинга: {form.target_channel or 'Отсутствует!'}\n" \
                   f"3. Глубина для поиска: {vfc.depth or 'Отсутствует!'}\n"
    bot.reply_to(message, preview_text)


def clear_data(message):
    form_dict[message.chat.id] = Form()
    if vfc_dict.get(message.chat.id):
        vfc_dict[message.chat.id].clear_user_data()
    bot.reply_to(message, "Данные очищены!")


@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(row_width=2)
    markup.add(types.KeyboardButton('Парсинг видео'))
    bot.send_message(message.chat.id, "Вас приветствует телеграм видео парсер!\nнажмите кнопку 'Парсинг видео'",
                     reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        if call.data.startswith("send_video_"):
            file_id = call.data[11:]
            chat = call.message.chat.id
            form = form_dict.get(chat)
            vfc_instance = vfc_dict.get(chat)
            params = vfc_instance.user_videos.get(file_id)
            bot.answer_callback_query(callback_query_id=call.id, text="Попытка отправить видео...")
            response = bot.send_video(chat_id=form.target_channel, **params)
            if response.error_code == 403:
                bot.send_message(chat, "Вам необходимо добавить в администраторы канала {} нашего бота {}".format(
                    form.target_channel, call.message.get("from")["first_name"]))
            elif response.message_id:
                bot.answer_callback_query(callback_query_id=call.id, text="Видео успешно отправлено!")
            else:
                bot.answer_callback_query(callback_query_id=call.id, text="Не удалось отправить видео!")
        elif call.data.startswith("delete_video_"):
            file_id = call.data[13:]
            vfc_instance = vfc_dict.get(call.message.chat.id)
            vfc_instance.user_videos.pop(file_id, None)
            bot.delete_message(call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(callback_query_id=call.id, text="Незарегестрированное нажатие!")
    except telebot.apihelper.ApiException as api_ex:
        _logging.error("Ошибка - {}".format(api_ex))
        bot.send_message(chat, "Вам необходимо добавить в администраторы канала {} нашего бота @{}".format(
            form.target_channel, call.message.from_user.username))
    except Exception as e:
        _logging.error(e)


@bot.message_handler(func=lambda message: True)
def echo_all(message):
    try:
        if message.text == 'Парсинг видео':
            user_id = message.chat.id
            form_dict[user_id] = Form()
            vfc_dict[user_id] = VideoFromChannel(chat_id=user_id, depth=1)
            parse_video_keyboard = types.ReplyKeyboardMarkup(row_width=2)
            parse_video_keyboard.add(types.KeyboardButton("Ввести ссылку"),
                                     types.KeyboardButton("Указать канал"),
                                     types.KeyboardButton("Проверить настройки"),
                                     types.KeyboardButton("Указать глубину"),
                                     types.KeyboardButton("Начать поиск"),
                                     types.KeyboardButton("Очистить"))
            bot.send_message(message.chat.id, INFO_MGS, reply_markup=parse_video_keyboard)
        elif message.text == "Начать поиск":
            search_start(message=message)
        elif message.text == "Ввести ссылку":
            if not form_dict.get(message.chat.id):
                form_dict[message.chat.id] = Form()
                vfc_dict[message.chat.id] = VideoFromChannel(chat_id=message.chat.id, depth=1)
            bot.reply_to(message, "Введите ссылку на пост с видео. (Только 1шт.)")
            bot.register_next_step_handler(message, get_data_step, "post_with_video", "URL-адрес поста с видео")
        elif message.text == "Указать канал":
            bot.reply_to(message, "Введите название канала вместе с символом `@`. Например: @your_channel.\n"
                                  "Эта ссылка необходима для отправки видео, то есть нужно указать канал, "
                                  "в который вы хотите отправлять все найденные видео")
            bot.register_next_step_handler(message, get_data_step, "target_channel", "ссылку на ваш канал")
        elif message.text == "Указать глубину":
            bot.reply_to(message, "Введите число, которое вы хотели бы установить для поиска. "
                                  "Например пост это альбом состоящий из трёх файлов, чтобы его "
                                  "обойти необходимо установить глубину `3`.")
            bot.register_next_step_handler(message, change_depth)
        elif message.text == 'Проверить настройки':
            print_user_data(message)
        elif message.text == 'Очистить':
            clear_data(message)
        else:
            bot.send_message(message.chat.id,
                             "Неудалось найди запрошенную вами функцию, воспользуйтесь командой /start")
    except Exception as e:
        bot.reply_to(message, 'Ошибка: %s' % e)


if __name__ == "__main__":
    while True:
        try:
            bot.enable_save_next_step_handlers(delay=1)
            bot.polling(none_stop=True)
        except KeyboardInterrupt:
            _logging.exception("Вы произвели остановку бота!")
            break
        except Exception as e:
            print(e)
            # повторяем через 30 секунд в случае недоступности сервера Telegram
            time.sleep(30)
