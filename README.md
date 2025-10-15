# TG Price Checker
Launch Telegram bot: https://t.me/btc_tracker1_bot
A minimal Telegram bot that streams BTC/USDT price from Binance and sends updates to chat:
- Only sends when the price changed by at least a configurable delta (USD)
- And not more often than a configurable delay (minutes)
- Inline buttons to change both on the fly (per chat)

Built with python-telegram-bot (v20+) and websockets.

## Features
- /start to begin receiving price updates
- /stop to stop updates
- /menu to open inline buttons:
  - Set time delay in minutes
  - Set price delta in dollars
- /status to see current settings
- Robust reconnects if the WebSocket drops

## Requirements
- Python 3.10+
- A Telegram bot token (get from @BotFather)

## Quick start
1) Clone the repo and enter the folder

```bash
git clone <your-repo-url>
cd tg_price_checker
```

2) Create and activate a virtual environment (macOS/Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3) Install dependencies

```bash
pip install -r requirements.txt
```

4) Configure environment

- Create a `.env` file in the project root with your bot token:

```env
TOKEN=123456789:abcdefghijklmnopqrstuvwxyz
```

5) Run the bot

```bash
python main.py
```

Open your bot in Telegram and use /start, /menu, /status.

## How it works
- The bot opens a WebSocket to `wss://fstream.binance.com/ws/btcusdt@aggTrade` and listens for trades.
- It sends the latest price message only when both are true:
  - at least `delay` minutes have passed since the last message, and
  - the absolute difference from the last sent price is at least `delta` USD.
- All settings and state are stored per-chat in `context.chat_data`.

## Commands
- /start — start streaming prices in this chat
- /stop — stop streaming prices in this chat
- /menu — configure delay (minutes) and delta (USD) via inline buttons
- /status — show current settings and whether the stream is running

## Configuration via buttons
- Tap “Set time delay in minutes” and reply with an integer ≥ 1 (e.g., `5`).
- Tap “Set price delta in dollars” and reply with a positive number (e.g., `10.5`).
- Changes apply immediately to the running stream.

## Troubleshooting
- CERTIFICATE_VERIFY_FAILED (self-signed):
  - For development, the code disables SSL verification for the Binance WebSocket to avoid failures behind corporate proxies. For production, enable verification:
    - In `main.py`, use `ssl.create_default_context()` as-is and remove lines that set `check_hostname=False` and `verify_mode=CERT_NONE`.
  - Alternatively, configure your system to trust the proxy’s root CA.
- Keepalive ping timeout (1011):
  - The bot sets `ping_interval` and `ping_timeout` and will automatically reconnect. Intermittent timeouts on poor networks are expected.
- Nothing happens on /stop:
  - Ensure the bot is running in the same chat you started it. The task is stored per chat. Try `/status`.



## License
MIT (or your choice).

solvit.space/projects/tg_bot_bitcoin
