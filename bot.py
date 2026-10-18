import json
import os
import sys
import time
import threading
from collections import OrderedDict

import requests
import websocket
from dotenv import load_dotenv, set_key

import config

ENV_FILE = ".env"


class TwitchTier3Bot:
    def __init__(self):
        self.access_token = config.BOT_ACCESS_TOKEN
        self.refresh_token = config.BOT_REFRESH_TOKEN

        self.broadcaster_token = config.BROADCASTER_ACCESS_TOKEN
        self.broadcaster_refresh_token = config.BROADCASTER_REFRESH_TOKEN

        self.broadcaster_id = config.BROADCASTER_ID
        self.bot_id = config.BOT_ID

        self.ws = None
        self.stop_event = threading.Event()

        # user_id -> (tier, expires_at)
        self.sub_cache = OrderedDict()
        self.cache_lock = threading.Lock()

        self.last_seen_message_ids = OrderedDict()
        self.message_lock = threading.Lock()

        self.current_session_id = None
        self.reconnect_url = None

    # ---------------------------------------------------------
    # OAuth/token management
    # ---------------------------------------------------------

    def headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Client-Id": config.CLIENT_ID,
        }

    def validate_token(self):
        r = requests.get(
            "https://id.twitch.tv/oauth2/validate",
            headers={"Authorization": f"OAuth {self.access_token}"},
            timeout=15,
        )
        return r.status_code == 200

    def refresh_access_token(self):
        if not self.refresh_token:
            raise RuntimeError("No refresh token. Run setup.py again.")

        print("[AUTH] Refreshing access token...")

        r = requests.post(
            "https://id.twitch.tv/oauth2/token",
            params={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": config.CLIENT_ID,
                "client_secret": config.CLIENT_SECRET,
            },
            timeout=20,
        )

        if r.status_code != 200:
            raise RuntimeError(f"Token refresh failed: {r.status_code} {r.text}")

        data = r.json()
        self.access_token = data["access_token"]

        # Twitch normally returns a new refresh token when rotating it.
        if data.get("refresh_token"):
            self.refresh_token = data["refresh_token"]

        set_key(ENV_FILE, "ACCESS_TOKEN", self.access_token)
        set_key(ENV_FILE, "REFRESH_TOKEN", self.refresh_token)

        print("[AUTH] Token refreshed and saved.")

    def ensure_token(self):
        if not self.access_token:
            raise RuntimeError("ACCESS_TOKEN is missing. Run setup.py.")

        if not self.validate_token():
            self.refresh_access_token()

        # Also check that the token is actually for this application.
        r = requests.get(
            "https://id.twitch.tv/oauth2/validate",
            headers={"Authorization": f"OAuth {self.access_token}"},
            timeout=15,
        )
        r.raise_for_status()

        data = r.json()

        if data.get("client_id") != config.CLIENT_ID:
            raise RuntimeError("ACCESS_TOKEN belongs to a different Twitch app.")

        if data.get("user_id") != self.bot_id:
            raise RuntimeError(
                "The authorized Twitch account is not the configured BOT_LOGIN."
            )

    # ---------------------------------------------------------
    # Twitch API
    # ---------------------------------------------------------

    def get_subscription_tier(self, user_id):

        now = time.time()

        cached = self.sub_cache.get(user_id)

        if cached:

            if cached[1] > now:
                return cached[0]

        response = requests.get(
            "https://api.twitch.tv/helix/subscriptions",
            headers={
                "Authorization": f"Bearer {self.broadcaster_token}",
                "Client-Id": config.CLIENT_ID,
            },
            params={
                "broadcaster_id": config.BROADCASTER_ID,
                "user_id": user_id,
            },
            timeout=10,
        )

        if response.status_code == 401:

            print("[AUTH] Broadcaster token expired.")

            self.refresh_broadcaster_token()

            response = requests.get(
                "https://api.twitch.tv/helix/subscriptions",
                headers={
                    "Authorization": f"Bearer {self.broadcaster_token}",
                    "Client-Id": config.CLIENT_ID,
                },
                params={
                    "broadcaster_id": config.BROADCASTER_ID,
                    "user_id": user_id,
                },
                timeout=10,
            )

        if response.status_code == 404:

            tier = None

        else:

            response.raise_for_status()

            data = response.json()

            subscriptions = data.get("data", [])

            if subscriptions:

                tier = subscriptions[0]["tier"]

            else:

                tier = None

        self.sub_cache[user_id] = (tier, now + config.SUBSCRIPTION_CACHE_SECONDS)

        return tier

    def delete_message(self, message_id):
        r = requests.delete(
            "https://api.twitch.tv/helix/moderation/chat",
            headers=self.headers(),
            params={
                "broadcaster_id": self.broadcaster_id,
                "moderator_id": self.bot_id,
                "message_id": message_id,
            },
            timeout=10,
        )

        if r.status_code == 204:
            return True

        if r.status_code == 401:
            self.refresh_access_token()

        print(f"[MOD] Delete failed: {r.status_code} {r.text}")
        return False

    # ---------------------------------------------------------
    # Message authorization
    # ---------------------------------------------------------

    def is_privileged(self, event):
        badges = event.get("badges") or []

        if config.ALLOW_BROADCASTER and event["chatter_user_id"] == self.broadcaster_id:
            return True

        if config.ALLOW_MODERATORS and "moderator" in badges:
            return True

        if config.ALLOW_VIPS and "vip" in badges:
            return True

        return False

    def process_chat_message(self, event):
        message_id = event.get("message_id")
        user_id = event.get("chatter_user_id")
        username = event.get("chatter_user_login", user_id)

        # EventSub can redeliver notifications. Ignore duplicates.
        with self.message_lock:
            if message_id in self.last_seen_message_ids:
                return
            self.last_seen_message_ids[message_id] = time.time()

            while len(self.last_seen_message_ids) > 10000:
                self.last_seen_message_ids.popitem(last=False)

        if self.is_privileged(event):
            print(f"[ALLOW] {username} (privileged)")
            return

        tier = self.get_subscription_tier(user_id)

        if tier == config.TIER_3:
            print(f"[ALLOW] {username} (Tier 3)")
            return

        # Non-Tier-3 user: remove message.
        print(f"[DELETE] {username} (tier={tier or 'none'})")
        self.delete_message(message_id)

    # ---------------------------------------------------------
    # EventSub WebSocket
    # ---------------------------------------------------------

    def subscribe(self, session_id):
        payload = {
            "type": "channel.chat.message",
            "version": "1",
            "condition": {
                "broadcaster_user_id": self.broadcaster_id,
                "user_id": self.bot_id,
            },
            "transport": {
                "method": "websocket",
                "session_id": session_id,
            },
        }

        r = requests.post(
            "https://api.twitch.tv/helix/eventsub/subscriptions",
            headers={
                **self.headers(),
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20,
        )

        if r.status_code != 202:
            raise RuntimeError(
                f"EventSub subscription failed: {r.status_code} {r.text}"
            )

        print("[EVENTSUB] channel.chat.message subscribed.")

    def on_message(self, ws, raw):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            print("[EVENTSUB] Invalid JSON received.")
            return

        message_type = data.get("metadata", {}).get("message_type")

        if message_type == "session_welcome":
            session = data["payload"]["session"]
            self.current_session_id = session["id"]
            self.reconnect_url = session.get("reconnect_url")

            print(f"[EVENTSUB] Connected. Session={self.current_session_id}")

            # We only subscribe for a brand-new session.
            self.subscribe(self.current_session_id)
            return

        if message_type == "session_keepalive":
            return

        if message_type == "notification":
            subscription = data["payload"].get("subscription", {})
            event = data["payload"].get("event", {})

            if subscription.get("type") == "channel.chat.message":
                self.process_chat_message(event)

            return

        if message_type == "session_reconnect":
            self.reconnect_url = data["payload"]["session"]["reconnect_url"]
            print("[EVENTSUB] Twitch requested a reconnect.")
            try:
                ws.close()
            except Exception:
                pass
            return

        if message_type == "revocation":
            print("[EVENTSUB] Subscription revoked:")
            print(json.dumps(data, indent=2))
            try:
                ws.close()
            except Exception:
                pass

    def on_error(self, ws, error):
        print(f"[EVENTSUB] WebSocket error: {error}")

    def on_close(self, ws, status_code, message):
        print(f"[EVENTSUB] WebSocket closed: {status_code} {message}")

    def connect_websocket(self, url):
        self.ws = websocket.WebSocketApp(
            url,
            on_open=lambda ws: print("[EVENTSUB] WebSocket opened."),
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )

        self.ws.run_forever(
            ping_interval=30,
            ping_timeout=10,
            origin="https://www.twitch.tv",
        )

    # ---------------------------------------------------------
    # Main loop
    # ---------------------------------------------------------

    def run(self):
        print("==============================================")
        print(" Twitch Tier-3-Only Chat Bot")
        print(" EventSub WebSocket")
        print("==============================================")
        print()

        self.ensure_token()

        if not self.broadcaster_id or not self.bot_id:
            raise RuntimeError("BROADCASTER_ID/BOT_ID missing. Run setup.py again.")

        # Start with a fresh WebSocket session.
        url = config.EVENTSUB_WS_URL

        while not self.stop_event.is_set():
            try:
                self.ensure_token()

                print(f"[EVENTSUB] Connecting to {url}")
                self.connect_websocket(url)

                # If Twitch supplied a reconnect URL, the existing
                # subscriptions migrate to the new session. Do not
                # create duplicate subscriptions.
                if self.reconnect_url:
                    url = self.reconnect_url
                    self.reconnect_url = None
                else:
                    url = config.EVENTSUB_WS_URL

            except KeyboardInterrupt:
                self.stop_event.set()
                break

            except Exception as exc:
                print(f"[MAIN] Error: {exc}")

                # An auth/API error can be fixed by refreshing once.
                try:
                    self.refresh_access_token()
                except Exception as refresh_exc:
                    print(f"[AUTH] Refresh failed: {refresh_exc}")

                time.sleep(5)

        print("Bot stopped.")


if __name__ == "__main__":
    try:
        TwitchTier3Bot().run()
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(0)
