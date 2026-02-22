# SMS Channel

The OpenClaw SDK includes a Twilio SMS integration for sending text messages
from your agents. The `TwilioSMSClient` provides an async interface using
`httpx` to call the Twilio REST API, with support for number whitelisting
and automatic message truncation.

## Quick Start

```python
import asyncio
from openclaw_sdk.channels.sms import SMSChannelConfig, TwilioSMSClient

async def main():
    config = SMSChannelConfig(
        account_sid="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        auth_token="your_auth_token",
        from_number="+15551234567",
    )

    client = TwilioSMSClient(config)
    message = await client.send_message(
        to="+15559876543",
        body="Hello from OpenClaw! Your report is ready.",
    )

    print(f"Sent: SID={message.sid}, Status={message.status}")

asyncio.run(main())
```

## SMSChannelConfig

Configuration model for the Twilio SMS channel. All fields are validated
by Pydantic.

| Parameter            | Type         | Default | Description                                       |
|----------------------|--------------|---------|---------------------------------------------------|
| `account_sid`        | `str`        | --      | Your Twilio Account SID                           |
| `auth_token`         | `str`        | --      | Your Twilio Auth Token                            |
| `from_number`        | `str`        | --      | The Twilio phone number to send from (E.164 format) |
| `allowed_numbers`    | `list[str]`  | `[]`    | Whitelist of allowed destination numbers          |
| `max_message_length` | `int`        | `1600`  | Maximum message body length before truncation     |

```python
from openclaw_sdk.channels.sms import SMSChannelConfig

config = SMSChannelConfig(
    account_sid="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    auth_token="your_auth_token",
    from_number="+15551234567",
    allowed_numbers=["+15559876543", "+15551111111"],
    max_message_length=160,
)
```

!!! warning "Keep credentials secure"
    Never hard-code your `account_sid` and `auth_token` in source files.
    Use environment variables or a secrets manager:
    ```python
    import os
    config = SMSChannelConfig(
        account_sid=os.environ["TWILIO_ACCOUNT_SID"],
        auth_token=os.environ["TWILIO_AUTH_TOKEN"],
        from_number=os.environ["TWILIO_FROM_NUMBER"],
    )
    ```

## TwilioSMSClient

The `TwilioSMSClient` handles all communication with the Twilio REST API.
It uses HTTP Basic auth constructed from your Account SID and Auth Token.

### Sending Messages

```python
client = TwilioSMSClient(config)

message = await client.send_message(
    to="+15559876543",
    body="Your order #1234 has shipped!",
)

print(message.sid)         # "SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
print(message.from_number) # "+15551234567"
print(message.to_number)   # "+15559876543"
print(message.body)        # "Your order #1234 has shipped!"
print(message.status)      # "queued"
```

The `send_message()` method:

1. Checks the destination number against `allowed_numbers` (if configured).
2. Truncates the message body to `max_message_length` characters.
3. Sends a `POST` to the Twilio Messages API.
4. Returns an `SMSMessage` with the response data.

### Parsing Incoming Webhooks

When Twilio sends an incoming SMS to your webhook endpoint, use
`parse_incoming_webhook()` to convert the raw form data into an `SMSMessage`:

```python
from openclaw_sdk.channels.sms import TwilioSMSClient, SMSMessage

# In your webhook handler (e.g. FastAPI, Flask)
def handle_incoming_sms(form_data: dict) -> SMSMessage:
    message = TwilioSMSClient.parse_incoming_webhook(form_data)
    print(f"From: {message.from_number}")
    print(f"Body: {message.body}")
    return message
```

The webhook parser extracts these Twilio fields:

| Twilio Field  | Maps To              |
|---------------|----------------------|
| `MessageSid`  | `message.sid`        |
| `From`        | `message.from_number`|
| `To`          | `message.to_number`  |
| `Body`        | `message.body`       |
| `SmsStatus`   | `message.status`     |

## SMSMessage

The `SMSMessage` Pydantic model represents both outgoing and incoming SMS messages.

| Field         | Type  | Default | Description                         |
|---------------|-------|---------|-------------------------------------|
| `sid`         | `str` | `""`    | Twilio Message SID                  |
| `from_number` | `str` | `""`    | Sender phone number (E.164 format)  |
| `to_number`   | `str` | `""`    | Recipient phone number              |
| `body`        | `str` | `""`    | Message body text                   |
| `status`      | `str` | `""`    | Message status (e.g. `"queued"`, `"sent"`, `"delivered"`) |

## Allowed Numbers Whitelist

When `allowed_numbers` is set in the config, `send_message()` will reject
any destination number not in the list by raising a `ValueError`. This is
useful for development, testing, and compliance scenarios where you want
to restrict which numbers your agent can text.

```python
config = SMSChannelConfig(
    account_sid="ACxxx",
    auth_token="xxx",
    from_number="+15551234567",
    allowed_numbers=["+15559876543"],  # Only this number is allowed
)

client = TwilioSMSClient(config)

# This works:
await client.send_message(to="+15559876543", body="OK")

# This raises ValueError:
await client.send_message(to="+15550000000", body="Blocked!")
# ValueError: Number +15550000000 not in allowed_numbers list
```

!!! tip "Empty list means no restriction"
    When `allowed_numbers` is an empty list (the default), all destination
    numbers are permitted. Set it explicitly to restrict access.

## Message Truncation

Messages longer than `max_message_length` (default 1600 characters) are
automatically truncated before sending. The default of 1600 accommodates
up to 10 standard SMS segments. Set a lower value if you want to enforce
single-segment messages:

```python
config = SMSChannelConfig(
    account_sid="ACxxx",
    auth_token="xxx",
    from_number="+15551234567",
    max_message_length=160,  # Single SMS segment
)
```

## Error Handling

The `TwilioSMSClient` raises standard exceptions that you should handle:

```python
import httpx
from openclaw_sdk.channels.sms import TwilioSMSClient

client = TwilioSMSClient(config)

try:
    message = await client.send_message(to="+15559876543", body="Hello!")
except ValueError as e:
    # Number not in allowed_numbers list
    print(f"Blocked: {e}")
except httpx.HTTPStatusError as e:
    # Twilio API returned an error (invalid number, auth failure, etc.)
    print(f"Twilio error {e.response.status_code}: {e.response.text}")
```

| Exception               | Cause                                            |
|--------------------------|--------------------------------------------------|
| `ValueError`            | Destination number not in `allowed_numbers`      |
| `httpx.HTTPStatusError` | Twilio API returned a non-2xx response           |

## Full Example with FastAPI

```python
import os
from fastapi import FastAPI, Form
from openclaw_sdk.channels.sms import SMSChannelConfig, TwilioSMSClient

app = FastAPI()

config = SMSChannelConfig(
    account_sid=os.environ["TWILIO_ACCOUNT_SID"],
    auth_token=os.environ["TWILIO_AUTH_TOKEN"],
    from_number=os.environ["TWILIO_FROM_NUMBER"],
)
sms_client = TwilioSMSClient(config)


@app.post("/sms/send")
async def send_sms(to: str, body: str):
    message = await sms_client.send_message(to=to, body=body)
    return {"sid": message.sid, "status": message.status}


@app.post("/sms/webhook")
async def receive_sms(
    MessageSid: str = Form(""),
    From: str = Form(""),
    To: str = Form(""),
    Body: str = Form(""),
    SmsStatus: str = Form(""),
):
    message = TwilioSMSClient.parse_incoming_webhook({
        "MessageSid": MessageSid,
        "From": From,
        "To": To,
        "Body": Body,
        "SmsStatus": SmsStatus,
    })
    print(f"Incoming from {message.from_number}: {message.body}")
    return {"status": "received"}
```
