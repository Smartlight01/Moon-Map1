from dotenv import load_dotenv
import os

load_dotenv()

# ========= DISCORD AUTH ========= #
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")
DISCORD_ROLE_ID = os.getenv("DISCORD_ROLE_ID")

# ========= FINNHUB / MARKET DATA ========= #
FINNHUB_TOKEN = os.getenv("FINNHUB_TOKEN")

# ========= TRADIER / POLYGON KEYS ========= #
TRADIER_ACCESS_TOKEN = os.getenv("TRADIER_ACCESS_TOKEN")
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
