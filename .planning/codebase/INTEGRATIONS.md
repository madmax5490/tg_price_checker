# External Integrations

**Analysis Date:** 2026-03-05

## APIs & External Services

**Cryptocurrency Data:**
- Binance Futures WebSocket Stream - Real-time BTC/USDT aggregate trade prices
  - Endpoint: `wss://fstream.binance.com/ws/btcusdt@aggTrade`
  - SDK/Client: `websockets==15.0.1` (raw WebSocket, no Binance SDK)
  - Auth: None required (public endpoint)
  - Protocol: WebSocket over TLS; SSL hostname verification disabled in `main.py:96-98`
  - Message format: JSON with field `"p"` containing price as string
  - Connection managed in `send_price_loop()` at `main.py:86`

**Messaging Platform:**
- Telegram Bot API - Sending messages and receiving user commands
  - SDK/Client: `python-telegram-bot==22.5`
  - Auth: Bot token via `TOKEN` env var, read from `.env` at `main.py:290`
  - Mode: Long polling (`app.run_polling()` at `main.py:307`)
  - Outbound calls: `context.bot.send_message()` for price updates and user replies

## Data Storage

**Databases:**
- None — no external database used

**In-Memory State:**
- `context.chat_data` (python-telegram-bot built-in per-chat dict) stores:
  - `price_task` — active `asyncio.Task` for the price loop
  - `delta` — minimum USD price change before sending (default: 2.0)
  - `interval_sec` — minimum seconds between sends (default: 60)
  - `last_sent_price` — last price value sent to user
  - `last_sent_at` — loop timestamp of last send
  - `awaiting_input` — state machine key for pending user input
- State is ephemeral: lost on process restart

**File Storage:**
- Local filesystem only: `.env` file for bot token

**Caching:**
- None

## Authentication & Identity

**Auth Provider:**
- Telegram Bot API token (static secret)
  - Implementation: token loaded via `dotenv.dotenv_values(".env").get("TOKEN")` in `main.py:290`
  - No per-user authentication or authorization beyond standard Telegram chat_id scoping
  - All commands accessible to any user who messages the bot

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry, Datadog, or similar)

**Logs:**
- stdlib `logging` at INFO level, output to stdout/stderr
- Log statements in `main.py`: connection events, cancellation, and connection failures per chat_id

## CI/CD & Deployment

**Hosting:**
- Not configured — intended for local execution or any Python-capable host

**CI Pipeline:**
- None detected

## Environment Configuration

**Required env vars:**
- `TOKEN` — Telegram Bot API token (obtain from @BotFather on Telegram)

**Secrets location:**
- `.env` file in project root (gitignored via `.gitignore`)
- `.env.example` at project root provides variable names without values

## Webhooks & Callbacks

**Incoming:**
- None — bot uses polling mode, not webhook mode

**Outgoing:**
- Binance WebSocket stream (`wss://fstream.binance.com/ws/btcusdt@aggTrade`) — one persistent connection per active chat, established in `send_price_loop()` at `main.py:86`

---

*Integration audit: 2026-03-05*
