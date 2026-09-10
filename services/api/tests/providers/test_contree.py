import pytest

from app.providers.base import ProviderUnavailable
from app.providers.contree import ContreeSandboxProvider


async def test_contree_provider_initializes_installed_sdk_without_network():
    async with ContreeSandboxProvider(
        token="test-token",
        project_id="test-project",
        base_url="https://api.tokenfactory.nebius.com/sandboxes",
    ) as provider:
        assert provider._sdk is not None


def test_contree_provider_requires_project_id():
    with pytest.raises(ProviderUnavailable, match="NEBIUS_PROJECT_ID"):
        ContreeSandboxProvider(
            token="test-token",
            project_id="",
            base_url="https://api.tokenfactory.nebius.com/sandboxes",
        )
