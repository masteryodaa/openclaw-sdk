# RUN: python examples/04_channel_config.py
"""Channel config — full channel lifecycle: configure, list, login, and remove.

Demonstrates: client.configure_channel(), client.list_channels(),
client.remove_channel(), client.channels.login(), channels.web_login_start/wait().
"""

import asyncio

from openclaw_sdk import OpenClawClient, ClientConfig, WhatsAppChannelConfig
from openclaw_sdk.gateway.mock import MockGateway


async def main() -> None:
    mock = MockGateway()
    await mock.connect()

    # Register mock responses for channel operations
    mock.register("config.get", {"raw": "{}", "exists": True, "path": "/mock"})
    mock.register("config.set", {"ok": True})
    mock.register(
        "channels.status",
        {
            "channelOrder": ["whatsapp", "telegram"],
            "channels": {
                "whatsapp": {"configured": True, "linked": False, "status": "disconnected"},
                "telegram": {"configured": False, "linked": False, "status": "unconfigured"},
            },
        },
    )
    mock.register(
        "web.login.start",
        {"qrDataUrl": "data:image/png;base64,MOCK_QR_DATA_HERE"},
    )
    mock.register(
        "web.login.wait",
        {"linked": True, "phone": "+15551234567"},
    )
    mock.register("channels.logout", {"ok": True})

    client = OpenClawClient(config=ClientConfig(), gateway=mock)

    # 1. Configure a WhatsApp channel (read-modify-write on gateway config)
    print("Configuring WhatsApp channel...")
    await client.configure_channel(WhatsAppChannelConfig(
        dm_policy="allowlist",
        allow_from=["+15551234567"],
        auto_reconnect=True,
    ))
    print("  Channel configured via config.set")

    # 2. List all channels
    print("\nAll channels:")
    channels = await client.list_channels()
    for ch in channels:
        print(f"  {ch['name']}: linked={ch.get('linked')}, status={ch.get('status')}")

    # 3. Start QR login via the shorthand login() method
    print("\nStarting WhatsApp QR login...")
    login_start = await client.channels.login()
    qr_url = login_start.get("qrDataUrl", "")
    print(f"  QR data URL length: {len(qr_url)} chars")
    print(f"  (In a real app you would render this QR code for the user to scan)")

    # 4. Wait for QR scan
    print("\nWaiting for QR scan...")
    login_result = await client.channels.web_login_wait(timeout_ms=10000)
    print(f"  Linked: {login_result.get('linked')}")
    print(f"  Phone : {login_result.get('phone', 'N/A')}")

    # 5. Remove / logout a channel
    print("\nRemoving WhatsApp channel...")
    removed = await client.remove_channel("whatsapp")
    print(f"  Removed: {removed}")

    await client.close()
    print("\nChannel lifecycle complete.")


if __name__ == "__main__":
    asyncio.run(main())
