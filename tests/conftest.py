"""Shared test fixtures."""
from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest

from openclaw_sdk.gateway.mock import MockGateway


@pytest.fixture
def mock_gateway() -> MockGateway:
    return MockGateway()


@pytest.fixture
async def connected_mock_gateway() -> AsyncGenerator[MockGateway, None]:
    gw = MockGateway()
    await gw.connect()
    yield gw
    await gw.close()
