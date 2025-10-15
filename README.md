# Telegram BTC/USDT Price Checker Bot

A Telegram bot that provides real-time Bitcoin (BTC/USDT) price updates from Binance with customizable notification settings.

## Features

- **Real-time Price Updates**: Connects to Binance WebSocket API to get live BTC/USDT prices
- **Customizable Notifications**: 
  - Set minimum time interval between notifications (in minutes)
  - Set minimum price change (delta) required to trigger a notification (in USD)
- **Smart Filtering**: Only sends updates when the price changes by your configured delta amount
- **Automatic Reconnection**: Handles connection failures gracefully with automatic reconnection
- **Per-Chat Configuration**: Each chat/user can have their own settings
- **Interactive Menu**: Easy-to-use inline keyboard for configuration

## Requirements

- Python 3.8 or higher
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

## Dependencies

The bot requires the following Python packages:
- `python-telegram-bot` - Telegram Bot API wrapper
- `python-dotenv` - Environment variable management
- `websockets` - WebSocket client for Binance API

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/madmax5490/tg_price_checker.git
   cd tg_price_checker
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   
   Or install manually:
   ```bash
   pip install python-telegram-bot python-dotenv websockets
   ```

3. **Configure the bot**
   
   Create a `.env` file in the project root directory:
   ```bash
   echo "TOKEN=your_telegram_bot_token_here" > .env
   ```
   
   Replace `your_telegram_bot_token_here` with your actual bot token from [@BotFather](https://t.me/botfather).

## Usage

### Starting the Bot

Run the bot with:
```bash
python main.py
```

### Bot Commands

Once the bot is running, you can interact with it using the following commands in Telegram:

- `/start` - Start receiving BTC/USDT price updates
- `/stop` - Stop receiving price updates
- `/menu` - Open the configuration menu to adjust settings
- `/status` - Check current bot status and settings
- `/hello` - Simple greeting command

### Configuration

Use the `/menu` command to access the interactive configuration menu, where you can:

1. **Set time delay in minutes**: Configure the minimum time interval between notifications
   - Example: Setting to `5` means you'll receive updates at most once every 5 minutes
   - Default: 1 minute

2. **Set price delta in dollars**: Configure the minimum price change required for notification
   - Example: Setting to `10.5` means you'll only be notified when the price changes by $10.50 or more
   - Default: $2.00

### How It Works

1. Start the bot with `/start`
2. The bot connects to Binance's WebSocket API and monitors BTC/USDT prices in real-time
3. When the price changes by at least your configured delta AND the configured time interval has passed since the last notification, you'll receive an update
4. Configure your preferences using `/menu` to customize notification frequency and sensitivity
5. Use `/status` to check if the bot is running and view your current settings

## Default Settings

- **Default time delay**: 60 seconds (1 minute)
- **Default price delta**: $2.00 USD

## Technical Details

- **Data Source**: Binance Futures WebSocket API (`wss://fstream.binance.com/ws/btcusdt@aggTrade`)
- **SSL Verification**: Currently disabled for compatibility (use with caution in production)
- **Connection Management**: Automatic reconnection with 10-second backoff on failures
- **WebSocket Settings**: 
  - Ping interval: 30 seconds
  - Ping timeout: 30 seconds
  - Close timeout: 10 seconds

## Error Handling

The bot includes robust error handling:
- Automatic reconnection on WebSocket failures
- Graceful task cancellation when stopping
- Connection failure notifications to users
- Comprehensive logging for debugging

## Development

The project structure is simple:
- `main.py` - Main bot application with all handlers and logic
- `.env` - Configuration file for the Telegram bot token
- `.gitignore` - Git ignore rules

## Security Notes

⚠️ **Important**: 
- Never commit your `.env` file or bot token to version control
- The SSL certificate verification is currently disabled in the code. For production use, consider enabling it by removing or modifying the SSL context configuration
- Keep your bot token secure and never share it publicly

## License

This project is open source and available for personal and educational use.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## Support

If you encounter any issues or have questions, please open an issue on the GitHub repository.
