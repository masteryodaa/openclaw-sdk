# Framework Integrations

Drop-in integrations for Django, Flask, Streamlit, Jupyter, and Celery.

## FastAPI

See the dedicated [FastAPI Integration](fastapi.md) guide for full details.

```python
from openclaw_sdk.integrations.fastapi import create_agent_router

app.include_router(create_agent_router(client, prefix="/agents"))
```

## Flask

```python
from openclaw_sdk.integrations.flask_app import create_agent_blueprint

app = Flask(__name__)
bp = create_agent_blueprint(client, url_prefix="/agents")
app.register_blueprint(bp)
```

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/agents/health` | Gateway health check |
| `POST` | `/agents/<agent_id>/execute` | Execute a query (JSON body: `{"query": "..."}`) |

## Django

```python
# settings.py or AppConfig.ready()
from openclaw_sdk.integrations.django_app import setup
setup(client)

# urls.py
from openclaw_sdk.integrations.django_app import get_urls
urlpatterns += get_urls()
```

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/openclaw/health/` | Gateway health check |
| `POST` | `/openclaw/agents/<agent_id>/execute/` | Execute a query |

## Streamlit

One-line chat widget for Streamlit apps:

```python
import streamlit as st
from openclaw_sdk.integrations.streamlit_ui import st_openclaw_chat

# Renders a full chat interface
st_openclaw_chat(agent, title="My AI Assistant")
```

**Options:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `title` | `"OpenClaw Chat"` | Chat title |
| `placeholder` | `"Type a message..."` | Input placeholder |
| `show_thinking` | `False` | Show agent thinking/reasoning |
| `show_token_usage` | `True` | Show token counts and latency |

## Jupyter / IPython

Magic commands for interactive notebooks:

```python
# Load the extension
%load_ext openclaw_sdk.integrations.jupyter_magic

# Connect to gateway
%openclaw_connect

# Execute queries (renders Markdown)
%openclaw What is the capital of France?

# Switch agent
%openclaw_agent data-analyst
%openclaw Analyze this dataset
```

## Celery

Queue agent executions as background tasks:

```python
from celery import Celery
from openclaw_sdk.integrations.celery_tasks import create_execute_task, create_batch_task

app = Celery("tasks", broker="redis://localhost:6379")

execute = create_execute_task(app, client)
batch = create_batch_task(app, client)

# Queue a single execution
execute.delay("research-bot", "Find AI trends")

# Queue batch execution
batch.delay("analyst", ["Query 1", "Query 2", "Query 3"])
```

## Installation

Each integration requires its framework as an optional dependency:

```bash
pip install "openclaw-sdk[fastapi]"   # FastAPI
pip install "openclaw-sdk[flask]"     # Flask
pip install "openclaw-sdk[django]"    # Django
pip install "openclaw-sdk[streamlit]" # Streamlit
pip install "openclaw-sdk[jupyter]"   # Jupyter/IPython
pip install "openclaw-sdk[celery]"    # Celery
```
