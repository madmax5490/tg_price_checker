from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import dotenv
import asyncio
import websockets
import json
import ssl
import time

price_task = None
current_price = 0
delta = 0.5 #update price delta


async def send_price(context, chat_id):
    uri = "wss://fstream.binance.com/ws/btcusdt@aggTrade"
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE #ssl check disable
    global current_price
    while True:
        try:
            async with websockets.connect(uri, ssl=ssl_context, ping_interval=20,  # keepalive timout
                                          ping_timeout=20) as websocket:
                print('connected')
                while True:
                    message = await websocket.recv()
                    price = json.loads(message)['p']
                    print(price)
                    if abs(float(price) - current_price) > delta:
                        await context.bot.send_message(chat_id, f"BTC/USDT price: {price}")
                        current_price = float(price)
                        print('current price:', current_price)
                    await asyncio.sleep(5)
        except Exception as e:
            await context.bot.send_message(chat_id, "Connection failed")
            print("connection failed")
            print(f"Error in send_price: {e}")
            await asyncio.sleep(10)  # Wait before reconnecting





async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """This command starts the bot and establishes the websockets connection"""

    global price_task
    chat_id = update.message.chat_id
    if price_task is None or price_task.done():
        price_task = asyncio.create_task(send_price(context, chat_id))
        await context.bot.send_message(chat_id, "Started sending price updates.")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """This command stops the bot and establishes the websockets disconnection"""

    global price_task
    chat_id = update.message.chat_id
    if price_task and not price_task.done():
        price_task.cancel()
        await context.bot.send_message(chat_id, "Stopped sending price updates.")
    else:
        await context.bot.send_message(chat_id, "No active price updates.")


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Hello {update.effective_user.first_name}')


token = dotenv.dotenv_values(".env").get("TOKEN")
app = ApplicationBuilder().token(token).build()
app.add_handler(CommandHandler("hello", hello))
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stop", stop))


app.run_polling()