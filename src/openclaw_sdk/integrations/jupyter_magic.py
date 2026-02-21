"""Jupyter/IPython magic commands for OpenClaw SDK.

Requires: ``pip install openclaw-sdk[jupyter]``

Usage in a notebook::

    %load_ext openclaw_sdk.integrations.jupyter_magic
    %openclaw_connect
    result = %openclaw ask "What is Python?"
    print(result.content)
"""
from __future__ import annotations

from typing import Any


_client: Any = None
_agent: Any = None


def load_ipython_extension(ipython: Any) -> None:
    """Called by IPython when loading the extension."""
    try:
        from IPython.core.magic import register_line_magic
    except ImportError as exc:
        raise ImportError(
            "IPython is required. Install with: pip install openclaw-sdk[jupyter]"
        ) from exc

    import asyncio

    @register_line_magic
    def openclaw_connect(line: str) -> None:
        """Connect to OpenClaw gateway. Usage: %openclaw_connect [ws://url]"""
        global _client, _agent  # noqa: PLW0603
        from openclaw_sdk import OpenClawClient

        loop = asyncio.get_event_loop()
        if line.strip():
            _client = loop.run_until_complete(
                OpenClawClient.connect(gateway_url=line.strip())
            )
        else:
            _client = loop.run_until_complete(OpenClawClient.connect())
        _agent = _client.get_agent("jupyter")
        print("Connected to OpenClaw. Default agent: 'jupyter'")

    @register_line_magic
    def openclaw(line: str) -> Any:
        """Execute a query. Usage: %openclaw <query>"""
        global _agent  # noqa: PLW0603
        if _client is None:
            print("Not connected. Run %openclaw_connect first.")
            return None

        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(_agent.execute(line))

        # Display nicely in notebook
        try:
            from IPython.display import Markdown, display
            display(Markdown(result.content))
        except ImportError:
            print(result.content)

        return result

    @register_line_magic
    def openclaw_agent(line: str) -> None:
        """Switch the default agent. Usage: %openclaw_agent <agent_id>"""
        global _agent  # noqa: PLW0603
        if _client is None:
            print("Not connected. Run %openclaw_connect first.")
            return
        _agent = _client.get_agent(line.strip())
        print(f"Switched to agent: '{line.strip()}'")
