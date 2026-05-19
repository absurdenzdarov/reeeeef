import asyncio
import hashlib
import os
import requests
import pandas as pd

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message


# =========================================
# НАСТРОЙКИ
# =========================================

BOT_TOKEN = "8142641225:AAE_BCU58ZX3DMOne-Q4cI6aUs2UWOpFkrs"

GROUP_NAME = "РМ-25-9-2"

FILE_URL = "https://docs.360.yandex.ru/docs/view?url=ya-disk-public%3A%2F%2FwlsDzWxYtmepORmaCzucIdL43o11AeptdKrtDwjRCx1lh2I%2BrjDaPPZDnNCCR%2BAFDqZvSgIch5AN9ddz7ydViQ%3D%3D%3A%2FЭУиК.xls&name=ЭУиК.xls&nosw=1"

DOWNLOAD_PATH = "schedule.xls"

CHECK_INTERVAL = 600


# =========================================
# TELEGRAM
# =========================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# =========================================
# СКАЧИВАНИЕ ФАЙЛА
# =========================================


def download_schedule():
    response = requests.get(FILE_URL)

    with open(DOWNLOAD_PATH, "wb") as file:
        file.write(response.content)

    print("Файл расписания скачан")


# =========================================
# HASH ФАЙЛА
# =========================================


def get_file_hash(path):
    if not os.path.exists(path):
        return None

    md5 = hashlib.md5()

    with open(path, "rb") as file:
        while chunk := file.read(4096):
            md5.update(chunk)

    return md5.hexdigest()


# =========================================
# ПАРСЕР XLS
# =========================================


def parse_schedule():
    asyncio.run(main())
