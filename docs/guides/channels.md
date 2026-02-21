# Channels

Channels connect your OpenClaw agent to messaging platforms — WhatsApp, Telegram,
Discord, Slack, and more. Once a channel is configured and authenticated, your agent
can send and receive messages on that platform automatically.

## Channel Manager

The `ChannelManager` is available as `client.channels` and handles authentication
and lifecycle for all channel connections.

```python
import asyncio
from openclaw_sdk import OpenClawClient

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        channels = client.channels

        # Check status of all channels
        status = await channels.status()
        for ch in status:
            print(f"{ch.name}: {ch.state}")

asyncio.run(main())
```

### Channel Manager Methods

| Method | Description |
|--------|-------------|
| `status()` | Returns connection state for all channels |
| `login(channel)` | Initiate login for a channel |
| `logout(channel)` | Disconnect and deauthorize a channel |
| `web_login_start(channel)` | Start a web-based login flow (returns QR data) |
| `web_login_wait(channel)` | Wait for the web login to complete |
| `request_pairing_code(channel, phone)` | Request a pairing code (WhatsApp) |

## Channel Configurations

Each platform has a typed configuration model. All extend the base `ChannelConfig`.

```python
from openclaw_sdk import (
    WhatsAppChannelConfig,
    TelegramChannelConfig,
    DiscordChannelConfig,
    SlackChannelConfig,
    GenericChannelConfig,
)
```

### WhatsApp

```python
from openclaw_sdk import WhatsAppChannelConfig

config = WhatsAppChannelConfig(
    name="my-whatsapp",
    phone_number="+1234567890",
    auto_reply=True,
    allowed_contacts=["+1987654321", "+1555000111"],
)
```

### Telegram

```python
from openclaw_sdk import TelegramChannelConfig

config = TelegramChannelConfig(
    name="my-telegram",
    bot_token="123456:ABC-DEF...",
    allowed_chats=[-1001234567890],
)
```

### Discord

```python
from openclaw_sdk import DiscordChannelConfig

config = DiscordChannelConfig(
    name="my-discord",
    bot_token="MTIz...",
    allowed_guilds=["1234567890"],
    allowed_channels=["general", "bot-commands"],
)
```

### Slack

```python
from openclaw_sdk import SlackChannelConfig

config = SlackChannelConfig(
    name="my-slack",
    bot_token="xoxb-...",
    app_token="xapp-...",
    allowed_channels=["C0123456789"],
)
```

!!! warning
    Store bot tokens and secrets in environment variables or a secrets manager.
    Never commit them to version control.

### Generic Channel

For platforms without a dedicated config class, use `GenericChannelConfig`.

```python
from openclaw_sdk import GenericChannelConfig

config = GenericChannelConfig(
    name="custom-sms",
    type="sms",
    settings={"provider": "twilio", "from_number": "+1555000999"},
)
```

## Configuring Channels on the Client

```python
import asyncio
from openclaw_sdk import OpenClawClient, WhatsAppChannelConfig

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        # Add a channel
        config = WhatsAppChannelConfig(name="whatsapp-main", phone_number="+1234567890")
        await client.configure_channel(config)

        # List all configured channels
        channels = await client.list_channels()
        for ch in channels:
            print(f"{ch.name} ({ch.type})")

        # Remove a channel
        await client.remove_channel("whatsapp-main")

asyncio.run(main())
```

## QR Code Login Flow

WhatsApp and some other channels require scanning a QR code to authenticate.

```python
import asyncio
from openclaw_sdk import OpenClawClient

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        channels = client.channels

        # Step 1: Start web login — returns QR code data
        qr_data = await channels.web_login_start("whatsapp")
        print(f"Scan this QR code: {qr_data.qr_url}")

        # Step 2: Wait for the user to scan
        result = await channels.web_login_wait("whatsapp")
        if result.success:
            print("WhatsApp connected successfully!")
        else:
            print(f"Login failed: {result.error}")

asyncio.run(main())
```

!!! tip
    For headless environments where QR scanning is impractical, use the pairing
    code flow instead: `channels.request_pairing_code("whatsapp", "+1234567890")`.

## Pairing Code Flow

An alternative to QR scanning for WhatsApp.

```python
import asyncio
from openclaw_sdk import OpenClawClient

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        channels = client.channels

        # Request a pairing code sent to the phone
        code = await channels.request_pairing_code("whatsapp", "+1234567890")
        print(f"Enter this code on your phone: {code.pairing_code}")

        # Wait for pairing to complete
        result = await channels.web_login_wait("whatsapp")
        print(f"Connected: {result.success}")

asyncio.run(main())
```

## Full Example

```python
import asyncio
import os
from openclaw_sdk import (
    OpenClawClient,
    TelegramChannelConfig,
    DiscordChannelConfig,
)

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        # Configure Telegram
        await client.configure_channel(
            TelegramChannelConfig(
                name="support-bot",
                bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
            )
        )

        # Configure Discord
        await client.configure_channel(
            DiscordChannelConfig(
                name="dev-bot",
                bot_token=os.environ["DISCORD_BOT_TOKEN"],
                allowed_channels=["bot-commands"],
            )
        )

        # Login to both channels
        channels = client.channels
        await channels.login("support-bot")
        await channels.login("dev-bot")

        # Verify status
        status = await channels.status()
        for ch in status:
            print(f"{ch.name}: {ch.state}")

asyncio.run(main())
```

!!! note
    Channel login state is persisted by OpenClaw. You do not need to re-authenticate
    after restarting the SDK client — only after an explicit `logout()` or token
    revocation.
