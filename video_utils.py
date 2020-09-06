import ini
from pyrogram import Client
from urllib.parse import urlparse
from pyrogram import InlineKeyboardMarkup, InlineKeyboardButton

config = ini.parse(open('config.ini').read())


class VideoFromChannel:
    def __init__(self, chat_id=None, depth=1):
        self.depth = depth
        self.chat_id = chat_id
        self.user_videos = {}
        print(config["Telegram"]["TOKEN"])
        self.client = Client("Video_parser_bot",
                             api_id=config["Telegram"]["api_id"],
                             api_hash=config["Telegram"]["api_hash"],
                             bot_token=config["Telegram"]["TOKEN"])

    def change_depth(self, new_depth=1):
        self.depth = new_depth
        return self.depth

    def clear_user_data(self):
        self.user_videos = {}

    def pop_user_video(self, file_id=''):
        item = self.user_videos.pop(file_id, None)
        if item:
            return True
        else:
            return False

    def get_video_from_url(self, _url=''):
        counter = 0
        self.client.start()
        url_data = urlparse(_url)
        chat, post_id = None, None
        try:
            if url_data.path:
                chat_and_post = url_data.path.split("/")[1:]
                if chat_and_post and len(chat_and_post) == 2:
                    chat, post_id = chat_and_post
                else:
                    return counter
                if chat and post_id:
                    posts = self.client.get_messages(chat_id=f"@{chat}", message_ids=list(
                        [x for x in range(int(post_id), int(post_id) + self.depth)]))
                else:
                    return counter
                for x in posts:
                    if x.empty:
                        continue
                    video = x.video
                    if video:
                        file_id = video.file_id
                        caption = x.caption or video.file_name
                        bot_caption = f"Разрешение: {video.width}X{video.height}\n{caption}"
                        markup = InlineKeyboardMarkup([[
                            InlineKeyboardButton("✅ Запостить ✅️️", callback_data=f"send_video_{file_id}"),
                            InlineKeyboardButton("❌ Закрыть ❌", callback_data=f"delete_video_{file_id}")]])

                        self.client.send_video(chat_id=self.chat_id, video=file_id, file_ref=video.file_ref,
                                               caption=bot_caption, reply_markup=markup)
                        self.user_videos[file_id] = {"data": file_id, "caption": caption}
                        counter += 1
            else:
                self.client.send_message(chat_id=self.chat_id, text=f"Некоректная ссылка!\nПроверьте: {_url}")
                return counter
        except Exception as e:
            self.client.send_message(chat_id=self.chat_id, text=f"Произошла ошибка при попытке отправки видео: {e}")
            print(e)
            return counter
        finally:
            self.client.stop()
        return counter

