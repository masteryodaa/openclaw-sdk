# RUN: python examples/04_channel_config.py
"""Channel config — check channel status and perform a web (QR) login flow."""

import asyncio

from openclaw_sdk import OpenClawClient, ClientConfig
from openclaw_sdk.gateway.mock import MockGateway


async def main() -> None:
    mock = MockGateway()
    await mock.connect()

    # Register mock responses for channel operations
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

    client = OpenClawClient(config=ClientConfig(), gateway=mock)

    # 1. Check channel status
    status = await client.channels.status()
    print("Channel status:")
    for name, info in status.get("channels", {}).items():
        print(f"  {name}: linked={info['linked']}, status={info['status']}")

    # 2. Start QR login for WhatsApp
    print("\nStarting WhatsApp QR login...")
    login_start = await client.channels.web_login_start("whatsapp")
    qr_url = login_start.get("qrDataUrl", "")
    print(f"  QR data URL length: {len(qr_url)} chars")
    print(f"  (In a real app you would render this QR code for the user to scan)")

    # 3. Wait for QR scan
    print("\nWaiting for QR scan...")
    login_result = await client.channels.web_login_wait("whatsapp", timeout_ms=10000)
    print(f"  Linked: {login_result.get('linked')}")
    print(f"  Phone : {login_result.get('phone', 'N/A')}")

    await client.close()
    print("\nChannel login flow complete.")


if __name__ == "__main__":
    asyncio.run(main())
