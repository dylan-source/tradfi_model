import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import yfinance as yf
from telegram import Update
from telegram.error import TimedOut
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Replace 'YOUR_BOT_TOKEN' with your bot token from BotFather
TOKEN = '7396058475:AAGzBpcllz4GMOMB09mod000hIjn5FC0Yk0'

# Set up logging to help with debugging and provide information
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def get_sp500_volatility():
    try:
        # Fetch data for the last 60 days to ensure we have enough trading days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)

        data = yf.download(
            "^GSPC",
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            interval="1d",
            progress=False  # Disable progress bar
        )

        if len(data) < 26:
            logging.error("Not enough data to calculate 25-day volatility.")
            return None

        # Ensure data is sorted by date in ascending order
        data = data.sort_index()
        data['Return'] = data['Adj Close'].pct_change()
        data = data.dropna(subset=['Return'])

        # Use the last 25 returns for volatility calculation
        window_returns = data['Return'].iloc[-25:]  # Last 25 returns including the most recent
        volatility = window_returns.std(ddof=1) * np.sqrt(252)  # Annualized volatility
        volatility = round(volatility * 100, 2)  # Return as percentage with two decimals
        return volatility

    except Exception as e:
        logging.error(f"Error fetching volatility data: {e}")
        return None

async def get_sp500_volatility_last_7_days():
    try:
        # Fetch data for the last 100 days to ensure we have enough data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=100)

        data = yf.download(
            "^GSPC",
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            interval="1d",
            progress=False  # Disable progress bar
        )

        if data.empty or len(data) < 32:  # Minimum data points needed
            logging.error("Not enough data to calculate volatility over the last 7 days.")
            return None

        # Ensure data is sorted by date in ascending order
        data = data.sort_index()
        data['Return'] = data['Adj Close'].pct_change()
        data = data.dropna(subset=['Return'])

        # Get the list of trading days
        trading_days = data.index.tolist()

        # Prepare a list to hold the results
        results = []

        # Get the indices of the last 7 trading days
        last_7_indices = list(range(len(trading_days) - 7, len(trading_days)))

        # Loop over the last 7 trading days
        for idx in last_7_indices:
            # For each date at position idx, we need to get the 25 returns up to and including that date
            if idx < 24:
                date = trading_days[idx].strftime('%Y-%m-%d')
                logging.warning(f"Not enough data for date: {date}")
                continue

            # Get data for the 25-day window ending on the date at idx
            window_returns = data['Return'].iloc[idx - 24: idx + 1]

            if len(window_returns) < 25:
                date = trading_days[idx].strftime('%Y-%m-%d')
                logging.warning(f"Not enough data for date: {date}")
                continue

            # Calculate volatility
            volatility = window_returns.std(ddof=1) * np.sqrt(252)
            volatility = round(volatility * 100, 2)

            # Get the date
            date = trading_days[idx].strftime('%Y-%m-%d')

            # Append to results
            results.append((date, volatility))

        return results

    except Exception as e:
        logging.error(f"Error fetching volatility data over last 7 days: {e}")
        return None

async def volatility(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        vol = await get_sp500_volatility()
        if vol is not None:
            await update.message.reply_text(f"The current 25-day S&P 500 volatility is: {vol:.2f}%")
        else:
            await update.message.reply_text("Sorry, I'm unable to fetch the volatility data at this time.")
    except TimedOut:
        logging.warning("Timed out while trying to send a message.")
        await update.message.reply_text("Sorry, I couldn't respond in time. Please try again.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        await update.message.reply_text("An error occurred. Please try again later.")

async def volatility7(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        results = await get_sp500_volatility_last_7_days()
        if results:
            message = "25-Day Volatility Over The Last 7 Trading Days:\n"
            for date, vol in results:
                # Format volatility to two decimal places
                message += f"{date} - {vol:.2f}%\n"
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("Sorry, I'm unable to fetch the volatility data at this time.")
    except TimedOut:
        logging.warning("Timed out while trying to send a message.")
        await update.message.reply_text("Sorry, I couldn't respond in time. Please try again.")
    except Exception as e:
        logging.error(f"An unexpected error occurred in volatility7: {e}")
        await update.message.reply_text("An error occurred. Please try again later.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.reply_text(
            "You can use the following commands:\n"
            "/volatility - Get the current 25-day S&P 500 volatility\n"
            "/volatility7 - Get the 25-day volatility over the last 7 trading days\n"
            "/help - Get a list of available commands\n"
            "/greet - Receive a greeting message"
        )
    except TimedOut:
        logging.warning("Timed out while trying to send a help message.")
    except Exception as e:
        logging.error(f"An unexpected error occurred in help_command: {e}")

async def greet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.reply_text("Hello! How can I assist you today?")
    except TimedOut:
        logging.warning("Timed out while trying to send a greeting.")
    except Exception as e:
        logging.error(f"An unexpected error occurred in greet: {e}")

def main():
    # Create the application using ApplicationBuilder with custom timeouts
    app = ApplicationBuilder().token(TOKEN).connect_timeout(10.0).read_timeout(20.0).build()

    # Add command handlers
    app.add_handler(CommandHandler("volatility", volatility))
    app.add_handler(CommandHandler("volatility7", volatility7))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("greet", greet))

    # Start the bot
    app.run_polling()

if __name__ == '__main__':
    main()
