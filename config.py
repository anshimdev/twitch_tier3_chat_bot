import os

from dotenv import load_dotenv


load_dotenv()


CLIENT_ID = os.getenv(
    "TWITCH_CLIENT_ID",
    ""
).strip()


CLIENT_SECRET = os.getenv(
    "TWITCH_CLIENT_SECRET",
    ""
).strip()


BROADCASTER_LOGIN = os.getenv(
    "BROADCASTER_LOGIN",
    ""
).strip().lower()


BOT_LOGIN = os.getenv(
    "BOT_LOGIN",
    ""
).strip().lower()


BROADCASTER_ID = os.getenv(
    "BROADCASTER_ID",
    ""
).strip()


BOT_ID = os.getenv(
    "BOT_ID",
    ""
).strip()


BROADCASTER_ACCESS_TOKEN = os.getenv(
    "BROADCASTER_ACCESS_TOKEN",
    ""
).strip()


BROADCASTER_REFRESH_TOKEN = os.getenv(
    "BROADCASTER_REFRESH_TOKEN",
    ""
).strip()


BOT_ACCESS_TOKEN = os.getenv(
    "BOT_ACCESS_TOKEN",
    ""
).strip()


BOT_REFRESH_TOKEN = os.getenv(
    "BOT_REFRESH_TOKEN",
    ""
).strip()


# --------------------------------------------------
# CHAT SETTINGS
# --------------------------------------------------

ALLOW_BROADCASTER = True

ALLOW_MODERATORS = True

ALLOW_VIPS = True


# --------------------------------------------------
# SUBSCRIPTION
# --------------------------------------------------

TIER_3 = "3000"

SUBSCRIPTION_CACHE_SECONDS = 30


# --------------------------------------------------
# EVENTSUB
# --------------------------------------------------

EVENTSUB_WS_URL = (
    "wss://eventsub.wss.twitch.tv/ws"
)