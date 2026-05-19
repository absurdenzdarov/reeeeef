import logging
import requests
import pandas as pd
import re
from io import BytesIO
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime, timedelta

# ===== НАСТРОЙКИ (ВСТАВЬТЕ СВОЙ ТОКЕН) =====
TOKEN = "8142641225:AAE_BCU58ZX3DMOne-Q4cI6aUs2UWOpFkrs"
PUBLIC_KEY = "Xc08g8WbTavdHQ"  # Ваш публичный ключ из ссылки
FILENAME = "ЭУиК.xls"          # Имя файла
GROUP_NAME = "РМ-25-9-2"

# ===== СКАЧИВАНИЕ С ЯНДЕКС.ДИСКА ЧЕРЕЗ API =====
def download_from_yadisk():
    """Скачивает файл с Яндекс.Диска по публичной ссылке"""
    # Получаем информацию о файлах в публичной папке
    api_url = "https://cloud-api.yandex.net/v1/disk/public/resources"
    response = requests.get(api_url, params={"public_key": PUBLIC_KEY})
    response.raise_for_status()
    data = response.json()
    
    # Ищем нужный файл
    file_url = None
    for item in data.get("_embedded", {}).get("items", []):
        if item.get("name") == FILENAME:
            file_url = item.get("file")
            break
    
    if not file_url:
        raise Exception(f"Файл {FILENAME} не найден в публичной папке")
    
    # Скачиваем файл
    file_response = requests.get(file_url)
    file_response.raise_for_status()
    return BytesIO(file_response.content)

# ===== ПАРСИНГ =====
def parse_schedule(file_data):
    xls = pd.ExcelFile(file_data)
    all_pairs = []
    
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        
        # Ищем колонку с нужной группой
        group_col = None
        header_row = None
        
        for i in range(min(30, len(df))):
            row = df.iloc[i].astype(str).str.strip()
            for j, val in enumerate(row):
                if GROUP_NAME in val:
                    group_col = j
                    header_row = i
                    break
            if group_col is not None:
                break
        
        if group_col is None:
            continue
        
        teacher_col = group_col + 1
        room_col = group_col + 2
        current_day = ""
        
        # Проходим по строкам
        for i in range(header_row + 1, len(df)):
            row = df.iloc[i]
            pair_num = str(row[1]).strip()
            
            # Проверяем номер пары
            if pair_num.isdigit() and 1 <= int(pair_num) <= 6:
                # День недели
                day_val = str(row[0]).strip()
                if day_val != 'nan' and any(d in day_val for d in ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']):
                    current_day = day_val
                
                # Время
                time_val = str(row[2]).strip()
                if time_val == 'nan':
                    continue
                
                # Данные
                subject = str(row[group_col]).strip()
                teacher = str(row[teacher_col]).strip()
                room = str(row[room_col]).strip()
                
                # Пропускаем пустые и классные часы
                if subject and subject != 'nan' and subject != 'Классный час' and 'Классный час' not in subject:
                    all_pairs.append({
                        'day': current_day,
                        'pair': pair_num,
                        'time': time_val,
                        'subject': subject,
                        'teacher': teacher,
                        'room': room
                    })
    
    return all_pairs

# ===== ФОРМАТИРОВАНИЕ =====
def format_schedule(pairs, filter_day=None):
    if not pairs:
        return "❌ Расписание не найдено. Проверьте файл."
    
    # Фильтруем по дню
    if filter_day:
        filtered = [p for p in pairs if filter_day in p['day']]
    else:
        filtered = pairs
    
    if not filtered:
        return f"📭 На {filter_day if filter_day else 'эту неделю'} пар нет."
    
    # Группируем по дням
    days = {}
    for p in filtered:
        days.setdefault(p['day'], []).append(p)
    
    # Сортируем пары
    for day in days:
        days[day].sort(key=lambda x: int(x['pair']))
    
    # Формируем сообщение
    result = []
    for day_name, day_pairs in days.items():
        result.append(f"📅 {day_name} — Группа: {GROUP_NAME}")
        result.append("")
        for p in day_pairs:
            result.append(f"{p['pair']}️⃣ ⏳ {p['time']}")
            result.append(f"👨‍👩‍👧‍👦: {GROUP_NAME}")
            result.append(f"📚: {p['subject']}")
            result.append(f"👨‍🏫: {p['teacher']}")
            result.append(f"🚪: {p['room']}")
            result.append("")
        result.append("=" * 35)
        result.append("")
    
    return "\n".join(result)

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
def get_today_name():
    weekdays = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    return weekdays[datetime.now().weekday()]

def get_tomorrow_name():
    weekdays = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    return weekdays[(datetime.now() + timedelta(days=1)).weekday()]

# ===== КОМАНДЫ БОТА =====
async def start(update: Update, context):
    await update.message.reply_text(
        f"🎓 **Бот расписания колледжа**\n\n"
        f"📌 Группа: **{GROUP_NAME}**\n"
        f"📁 Источник: Яндекс.Диск (обновляется автоматически)\n\n"
        f"🔹 `/today` — расписание на сегодня\n"
        f"🔹 `/tomorrow` — на завтра\n"
        f"🔹 `/week` — на всю неделю",
        parse_mode='Markdown'
    )

async def today(update: Update, context):
    msg = await update.message.reply_text("⏳ Загружаю свежее расписание с Яндекс.Диска...")
    try:
        file_data = download_from_yadisk()
        pairs = parse_schedule(file_data)
        text = format_schedule(pairs, get_today_name())
        await msg.edit_text(text[:4096])
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {str(e)[:200]}\n\nПроверьте доступность файла на Яндекс.Диске.")

async def tomorrow(update: Update, context):
    msg = await update.message.reply_text("⏳ Загружаю расписание на завтра...")
    try:
        file_data = download_from_yadisk()
        pairs = parse_schedule(file_data)
        text = format_schedule(pairs, get_tomorrow_name())
        await msg.edit_text(text[:4096])
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {str(e)[:200]}")

async def week(update: Update, context):
    msg = await update.message.reply_text("⏳ Загружаю расписание на неделю...")
    try:
        file_data = download_from_yadisk()
        pairs = parse_schedule(file_data)
        text = format_schedule(pairs)
        # Разбиваем на части
        for i in range(0, len(text), 4000):
            await update.message.reply_text(text[i:i+4000])
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {str(e)[:200]}")

# ===== ЗАПУСК =====
def main():
    if TOKEN == "ВАШ_ТОКЕН_ОТ_BOTFATHER":
        print("❌ ОШИБКА: Вставьте свой токен в переменную TOKEN!")
        print("Получить токен можно у @BotFather в Telegram")
        return
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("tomorrow", tomorrow))
    app.add_handler(CommandHandler("week", week))
    
    print(f"✅ Бот запущен!")
    print(f"📁 Публичный ключ: {PUBLIC_KEY}")
    print(f"📄 Файл: {FILENAME}")
    print(f"👥 Группа: {GROUP_NAME}")
    app.run_polling()

if __name__ == "__main__":
    main()
