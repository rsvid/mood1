import requests
import asyncio
from datetime import datetime, timedelta
from telegram.ext import Application
from collections import deque

TOKEN = "8556399765:AAGIUjCx0NfFp53F4T0BQ0-hTuYw06jR6EA"
CHAT_ID = "-1002912708659"
API_URL = "https://futures.mexc.com/api/v1/contract/ticker?symbol=MOODENG_USDT"

CHECK_INTERVAL = 10
MAX_RECORDS = 30

price_history = deque(maxlen=MAX_RECORDS)
application = Application.builder().token(TOKEN).build()

def get_current_price():
    try:
        response = requests.get(API_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        price = float(data["data"]["lastPrice"])
        return price
    except Exception as e:
        print(f"Ошибка получения цены: {e}")
        return None

async def check_price_change(current_price):
    if len(price_history) == 0:
        return None

    current_time = datetime.now()
    five_minutes_ago = current_time - timedelta(minutes=5)

    for record_time, old_price in list(price_history):
        if record_time < five_minutes_ago:
            continue

        if old_price > 0:
            change_percent = ((current_price - old_price) / old_price) * 100

            if abs(change_percent) >= 5:
                return {
                    'old_price': old_price,
                    'change_percent': change_percent,
                    'record_time': record_time
                }

    return None

async def format_message(current_price, change_data):
    change_percent = change_data['change_percent']
    formatted_percent = f"+{change_percent:.2f}%" if change_percent > 0 else f"{change_percent:.2f}%"

    emoji = "🟢" if change_percent > 0 else "🔴"

    prices = [price for _, price in price_history]
    prices.append(current_price)
    max_price = max(prices)
    min_price = min(prices)

    old_time_str = change_data['record_time'].strftime("%H:%M:%S")

    message = f"""{emoji} Изм.: {formatted_percent}

Actual: {current_price:.6f} USDT

📈 MAX: {max_price:.6f} USDT
📉 MIN: {min_price:.6f} USDT"""

    return message

async def send_price():
    while True:
        try:
            current_price = get_current_price()

            if current_price is not None:
                current_time = datetime.now()
                price_history.append((current_time, current_price))

                change_data = await check_price_change(current_price)

                if change_data:
                    message = await format_message(current_price, change_data)
                    await application.bot.send_message(chat_id=CHAT_ID, text=message)

            await asyncio.sleep(CHECK_INTERVAL)

        except Exception as e:
            print(f"Ошибка в основном цикле: {e}")
            await asyncio.sleep(CHECK_INTERVAL)

async def main():
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    try:
        await send_price()
    finally:
        await application.stop()
        await application.shutdown()

if __name__ == "__main__":
    asyncio.run(main())