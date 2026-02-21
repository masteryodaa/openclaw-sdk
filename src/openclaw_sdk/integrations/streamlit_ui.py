"""Streamlit chat widget for OpenClaw SDK.

Requires: ``pip install openclaw-sdk[streamlit]``
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openclaw_sdk.core.agent import Agent


def st_openclaw_chat(
    agent: Agent,
    *,
    title: str = "OpenClaw Chat",
    placeholder: str = "Type a message...",
    show_thinking: bool = False,
    show_token_usage: bool = True,
) -> None:
    """Render an OpenClaw chat interface in Streamlit.

    Example::

        import streamlit as st
        from openclaw_sdk.integrations.streamlit_ui import st_openclaw_chat

        st_openclaw_chat(agent, title="My AI Assistant")
    """
    try:
        import streamlit as st
    except ImportError as exc:
        raise ImportError(
            "Streamlit is required. Install with: pip install openclaw-sdk[streamlit]"
        ) from exc

    import asyncio

    st.title(title)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input(placeholder):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                loop = asyncio.new_event_loop()
                try:
                    result = loop.run_until_complete(agent.execute(prompt))
                finally:
                    loop.close()

                st.markdown(result.content)

                if show_thinking and result.thinking:
                    with st.expander("Thinking"):
                        st.text(result.thinking)

                if show_token_usage and result.token_usage:
                    st.caption(
                        f"Tokens: {result.token_usage.input} in / "
                        f"{result.token_usage.output} out | "
                        f"{result.latency_ms}ms"
                    )

        st.session_state.messages.append({
            "role": "assistant",
            "content": result.content,
        })
