import os
import requests
from urllib.parse import urlencode

# Load from environment
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")
ROLE_ID = os.getenv("DISCORD_ROLE_ID")

API_BASE = "https://discord.com/api"


def get_authorize_url():
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "identify guilds.members.read"
    }
    return f"{API_BASE}/oauth2/authorize?{urlencode(params)}"


def exchange_code(code: str):
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = requests.post(f"{API_BASE}/oauth2/token", data=payload, headers=headers)

    return r.json()


def get_user(access_token: str):
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get(f"{API_BASE}/users/@me", headers=headers)
    return r.json()


def get_member(access_token: str):
    """
    Gets the logged-in user's membership info for the target server.
    Requires the scope: guilds.members.read
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"{API_BASE}/users/@me/guilds/{GUILD_ID}/member"
    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        return None

    return r.json()


def user_has_role(member_json: dict):
    """
    Check if the user has the required VIP role.
    """
    if not member_json:
        return False
    
    roles = member_json.get("roles", [])
    return ROLE_ID in roles
