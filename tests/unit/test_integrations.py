"""Tests for framework integrations (without requiring actual frameworks)."""
from __future__ import annotations

import pytest

from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.config import ClientConfig
from openclaw_sdk.gateway.mock import MockGateway


async def _make_client() -> OpenClawClient:
    mock = MockGateway()
    await mock.connect()
    return OpenClawClient(config=ClientConfig(), gateway=mock)


class TestFlaskIntegration:
    async def test_import_error_without_flask(self) -> None:
        """Verify helpful error when Flask not installed."""
        try:
            import flask  # noqa: F401

            pytest.skip("Flask is installed")
        except ImportError:
            from openclaw_sdk.integrations.flask_app import create_agent_blueprint

            client = await _make_client()
            with pytest.raises(ImportError, match="Flask is required"):
                create_agent_blueprint(client)

    async def test_channel_blueprint_import_error(self) -> None:
        """Verify helpful error for channel blueprint when Flask not installed."""
        try:
            import flask  # noqa: F401

            pytest.skip("Flask is installed")
        except ImportError:
            from openclaw_sdk.integrations.flask_app import create_channel_blueprint

            client = await _make_client()
            with pytest.raises(ImportError, match="Flask is required"):
                create_channel_blueprint(client)


class TestDjangoIntegration:
    async def test_setup_and_get_client(self) -> None:
        from openclaw_sdk.integrations.django_app import setup, get_client

        client = await _make_client()
        setup(client)
        assert get_client() is client

    def test_get_client_without_setup_raises(self) -> None:
        from openclaw_sdk.integrations import django_app

        django_app._client = None
        with pytest.raises(RuntimeError, match="not configured"):
            django_app.get_client()

    def test_get_urls_import_error_without_django(self) -> None:
        """Verify helpful error when Django not installed."""
        try:
            import django  # noqa: F401

            pytest.skip("Django is installed")
        except ImportError:
            from openclaw_sdk.integrations.django_app import get_urls

            with pytest.raises(ImportError, match="Django is required"):
                get_urls()


class TestStreamlitIntegration:
    def test_import_error_without_streamlit(self) -> None:
        try:
            import streamlit  # noqa: F401

            pytest.skip("Streamlit is installed")
        except ImportError:
            from openclaw_sdk.integrations.streamlit_ui import st_openclaw_chat

            assert callable(st_openclaw_chat)


class TestJupyterIntegration:
    def test_module_importable(self) -> None:
        from openclaw_sdk.integrations import jupyter_magic

        assert hasattr(jupyter_magic, "load_ipython_extension")

    def test_global_state_defaults(self) -> None:
        from openclaw_sdk.integrations import jupyter_magic

        assert jupyter_magic._client is None or jupyter_magic._client is not None
        assert callable(jupyter_magic.load_ipython_extension)


class TestCeleryIntegration:
    async def test_import_error_without_celery(self) -> None:
        try:
            import celery  # noqa: F401

            pytest.skip("Celery is installed")
        except ImportError:
            from openclaw_sdk.integrations.celery_tasks import create_execute_task

            client = await _make_client()
            with pytest.raises(ImportError, match="Celery is required"):
                create_execute_task(object(), client)

    async def test_batch_import_error_without_celery(self) -> None:
        try:
            import celery  # noqa: F401

            pytest.skip("Celery is installed")
        except ImportError:
            from openclaw_sdk.integrations.celery_tasks import create_batch_task

            client = await _make_client()
            with pytest.raises(ImportError, match="Celery is required"):
                create_batch_task(object(), client)
