import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask
import threading  # Import threading for running bot in a separate thread
import asyncio

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
# Render provides the PORT environment variable
PORT = int(os.getenv("PORT", 5000))  # Default to 5000 if PORT is not set

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

app = Flask(__name__)


@app.route("/")
def home():
    """Simple endpoint to keep the service alive."""
    return "Discord bot is running!"


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("------")
    # You might want to sync commands here if using app commands
    # await bot.tree.sync()
    print("Bot is ready.")


async def load_cogs():
    """Loads the bot's command cogs."""
    try:
        await bot.load_extension("src.cogs.bgg_commands")
        print("Cogs loaded successfully.")
    except Exception as e:
        print(f"Failed to load cogs: {e}")


# Function to run the bot's async loop in a separate thread
def run_bot_thread():
    """Runs the Discord bot in its own thread."""
    # Need to set a new event loop for the new thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Load cogs within the bot's event loop context
    loop.run_until_complete(load_cogs())

    # Start the bot (this is a blocking call)
    try:
        print("Starting Discord bot...")
        loop.run_until_complete(bot.start(TOKEN))
    except Exception as e:
        print(f"Error running bot in thread: {e}")
    finally:
        print("Discord bot thread shutting down.")
        loop.close()


# Start the bot in a separate thread when this script is imported/run
# This ensures the bot starts when gunicorn imports the 'app' object
print("Starting bot thread...")
bot_thread = threading.Thread(target=run_bot_thread)
bot_thread.start()

# The Flask app 'app' is the entry point for gunicorn
# gunicorn bot:app will run the Flask app, and the bot will be running in the background thread.

# For local testing, you might still want a __main__ block
if __name__ == "__main__":
    print("Running Flask app locally...")
    # In a local environment, you might run Flask directly
    # In production (Render with gunicorn), gunicorn handles this
    # Running with debug=True is not recommended in production
    app.run(host="0.0.0.0", port=PORT)
