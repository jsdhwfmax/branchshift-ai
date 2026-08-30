from app.providers.contree import ContreeSandboxProvider


async def test_contree_provider_initializes_installed_sdk_without_network():
    async with ContreeSandboxProvider(
        token="test-token",
        base_url="https://api.tokenfactory.nebius.com/sandboxes",
    ) as provider:
        assert provider._sdk is not None

