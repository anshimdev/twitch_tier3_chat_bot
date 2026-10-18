# Twitch Tier-3-Only Chat Bot

This bot runs next to StreamElements and removes messages from anyone who is not Tier 3.

## Behavior

Default:

- Tier 3: ALLOW
- Tier 2: DELETE
- Tier 1: DELETE
- Non-subscriber: DELETE
- Broadcaster: ALLOW
- Moderator: ALLOW
- VIP: ALLOW

You can change VIP behavior in `config.py`.

## Twitch developer application

Create an application in the Twitch Developer Console.

Use this exact OAuth redirect URL:

http://localhost:3000/callback

The application needs a Client ID and Client Secret.

## .env

Copy `.env.example` to `.env` and set:

TWITCH_CLIENT_ID
TWITCH_CLIENT_SECRET
BROADCASTER_LOGIN
BOT_LOGIN

Do not publish `.env`.

## Bot account

Use a separate Twitch account as the bot.

Log in to the broadcaster account and run:

/mod BOT_USERNAME

For example:

/mod mychannel_bot

The bot must be a moderator because Twitch requires moderator authorization for deleting chat messages.

## Setup

Double-click:

setup_bot.bat

A Twitch authorization page opens.

Authorize the BOT account.

The setup script stores the access token, refresh token, broadcaster ID and bot ID in `.env`.

## Start

Double-click:

start_bot.bat

Leave the window running while streaming.

## Twitch chat settings

Do NOT enable Twitch Subscriber-Only Mode if you want non-subscribers to be deleted by this bot.

The bot itself enforces the Tier-3 rule.

You can still use StreamElements for alerts, commands, timers and other moderation.

## Important

There is a small delay between a message being sent and the bot deleting it. Twitch does not provide a native "Tier 3 only" chat mode; the bot implements it by receiving chat messages and deleting messages that don't meet the rule.

## Security

Never share:

- TWITCH_CLIENT_SECRET
- ACCESS_TOKEN
- REFRESH_TOKEN
- .env

If you accidentally expose a token, revoke/reauthorize it.

## Troubleshooting

### 403 when deleting messages

Make sure the bot account is a moderator:

/mod BOT_USERNAME

Also run setup again so the bot gets the `moderator:manage:chat_messages` scope.

### EventSub authorization error

Run:

setup_bot.bat

and authorize the BOT account, not the broadcaster account.

### No messages received

Make sure:

1. BOT_LOGIN is correct.
2. BOT account is in the channel.
3. BOT account is a moderator.
4. setup.py was authorized successfully.
5. The channel is not using settings that prevent the bot from participating.

### StreamElements

StreamElements does not need to be removed or changed. It can continue operating as a moderator/bot independently.
