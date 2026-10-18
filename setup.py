import os
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs

import requests
from dotenv import load_dotenv, set_key


ENV_FILE = Path(".env")
REDIRECT_URI = "http://localhost:3000/callback"

load_dotenv(ENV_FILE)

CLIENT_ID = os.getenv("TWITCH_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET", "").strip()

BROADCASTER_LOGIN = os.getenv(
    "BROADCASTER_LOGIN", ""
).strip().lower()

BOT_LOGIN = os.getenv(
    "BOT_LOGIN", ""
).strip().lower()


class CallbackHandler(BaseHTTPRequestHandler):

    code = None
    error = None

    def do_GET(self):

        parsed = urlparse(self.path)

        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return

        params = parse_qs(parsed.query)

        CallbackHandler.code = params.get(
            "code",
            [None]
        )[0]

        CallbackHandler.error = params.get(
            "error",
            [None]
        )[0]

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8"
        )
        self.end_headers()

        if CallbackHandler.code:

            message = """
            <h2>Twitch authorization successful.</h2>
            <p>You can close this window.</p>
            """

        else:

            message = f"""
            <h2>Authorization failed.</h2>
            <p>{CallbackHandler.error}</p>
            """

        self.wfile.write(
            f"""
            <html>
            <body>
            {message}
            </body>
            </html>
            """.encode()
        )

    def log_message(self, format, *args):
        pass


def authorize(account_name, scopes):

    print()
    print("=" * 60)
    print(f"AUTHORIZE: {account_name}")
    print("=" * 60)

    print()
    print(
        f"Make sure your browser is logged into:"
    )

    print(
        f"    {account_name}"
    )

    print()

    auth_url = (
        "https://id.twitch.tv/oauth2/authorize?"
        + urlencode({
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(scopes),
        })
    )

    CallbackHandler.code = None
    CallbackHandler.error = None

    server = HTTPServer(
        ("127.0.0.1", 3000),
        CallbackHandler
    )

    server.timeout = 1

    webbrowser.open(auth_url)

    deadline = time.time() + 300

    while (
        time.time() < deadline
        and CallbackHandler.code is None
        and CallbackHandler.error is None
    ):

        server.handle_request()

    server.server_close()

    if not CallbackHandler.code:

        raise RuntimeError(
            f"Authorization failed: "
            f"{CallbackHandler.error}"
        )

    response = requests.post(
        "https://id.twitch.tv/oauth2/token",
        params={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": CallbackHandler.code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
        },
        timeout=20,
    )

    response.raise_for_status()

    return response.json()


def get_user(login, token):

    response = requests.get(
        "https://api.twitch.tv/helix/users",
        headers={
            "Authorization": f"Bearer {token}",
            "Client-Id": CLIENT_ID,
        },
        params={
            "login": login
        },
        timeout=20,
    )

    response.raise_for_status()

    users = response.json()["data"]

    if not users:

        raise RuntimeError(
            f"Twitch user not found: {login}"
        )

    return users[0]


def main():

    if not CLIENT_ID:
        raise SystemExit(
            "TWITCH_CLIENT_ID missing from .env"
        )

    if not CLIENT_SECRET:
        raise SystemExit(
            "TWITCH_CLIENT_SECRET missing from .env"
        )

    if not BROADCASTER_LOGIN:
        raise SystemExit(
            "BROADCASTER_LOGIN missing from .env"
        )

    if not BOT_LOGIN:
        raise SystemExit(
            "BOT_LOGIN missing from .env"
        )

    # --------------------------------------------------
    # BROADCASTER TOKEN
    # --------------------------------------------------

    broadcaster_scopes = [
        "channel:read:subscriptions",
        "channel:bot",
    ]

    print()
    print("STEP 1/2")
    print("Authorize your BROADCASTER account.")

    broadcaster_token = authorize(
        BROADCASTER_LOGIN,
        broadcaster_scopes
    )

    broadcaster = get_user(
        BROADCASTER_LOGIN,
        broadcaster_token["access_token"]
    )

    # --------------------------------------------------
    # BOT TOKEN
    # --------------------------------------------------

    bot_scopes = [
        "user:read:chat",
        "user:bot",
        "moderator:manage:chat_messages",
    ]

    print()
    print("STEP 2/2")
    print("Authorize your BOT account.")

    bot_token = authorize(
        BOT_LOGIN,
        bot_scopes
    )

    bot = get_user(
        BOT_LOGIN,
        bot_token["access_token"]
    )

    # --------------------------------------------------
    # SAVE EVERYTHING
    # --------------------------------------------------

    set_key(
        str(ENV_FILE),
        "BROADCASTER_ID",
        broadcaster["id"]
    )

    set_key(
        str(ENV_FILE),
        "BOT_ID",
        bot["id"]
    )

    set_key(
        str(ENV_FILE),
        "BROADCASTER_ACCESS_TOKEN",
        broadcaster_token["access_token"]
    )

    set_key(
        str(ENV_FILE),
        "BROADCASTER_REFRESH_TOKEN",
        broadcaster_token["refresh_token"]
    )

    set_key(
        str(ENV_FILE),
        "BOT_ACCESS_TOKEN",
        bot_token["access_token"]
    )

    set_key(
        str(ENV_FILE),
        "BOT_REFRESH_TOKEN",
        bot_token["refresh_token"]
    )

    print()
    print("=" * 60)
    print("SETUP COMPLETE")
    print("=" * 60)

    print()
    print(
        f"Broadcaster: "
        f"{broadcaster['login']}"
    )

    print(
        f"Broadcaster ID: "
        f"{broadcaster['id']}"
    )

    print()

    print(
        f"Bot: "
        f"{bot['login']}"
    )

    print(
        f"Bot ID: "
        f"{bot['id']}"
    )

    print()
    print("Now log into the broadcaster account and run:")
    print()
    print(
        f"/mod {BOT_LOGIN}"
    )

    print()
    print("Then run:")
    print()
    print(
        "python bot.py"
    )


if __name__ == "__main__":
    main()