import aiohttp
import os

from aiogram import Bot, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor


proxy_host = os.environ.get('PROXY', None)
proxy_credentials = os.environ.get('PROXY_CREDS', None)
if proxy_credentials:
    login, password = proxy_credentials.split(':')
    proxy_auth = aiohttp.BasicAuth(login=login, password=password)
else:
    proxy_auth = None


bot = Bot(token=os.environ['BOT_TOKEN'],
          proxy=proxy_host, proxy_auth=proxy_auth,
          parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.reply("Привет\nЯ бот, который знает о кино все!😎\n" 
                        "Введите команду /s, /search или /поиск и я помогу найти вам любой фильм")


async def on_shutdown(dp):
    await bot.close()
    await storage.close()

if __name__ == '__main__':
    from handlers import dp
    executor.start_polling(dp)

# PROXY=socks5://178.128.203.1:1080 PROXY_CREDS=student:TH8FwlMMwWvbJF8FYcq0 BOT_TOKEN=1013702296:AAHaUfPLWpuuqadLlrMv0co0w0iVIkM08-U python3 main.py