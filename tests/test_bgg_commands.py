import pytest
import discord
from discord.ext import commands
from unittest.mock import AsyncMock, MagicMock, patch

# Adjust the import path based on the project structure
# Assuming tests are run from the root directory
from src.cogs.bgg_commands import BggCommands
from src.bgg_api import BGGClient


@pytest.fixture
def mock_bot():
    """Fixture for a mocked discord.ext.commands.Bot."""
    return AsyncMock(spec=commands.Bot)


@pytest.fixture
def mock_context():
    """Fixture for a mocked discord.ext.commands.Context."""
    ctx = AsyncMock(spec=commands.Context)
    ctx.defer = AsyncMock()
    ctx.send = AsyncMock()
    ctx.author = MagicMock(spec=discord.User)
    ctx.author.id = 123456789
    ctx.author.display_name = "TestUser"
    return ctx


@pytest.fixture
def mock_bgg_client():
    """Fixture for a mocked BGGClient."""
    client = MagicMock(spec=BGGClient)
    client.search_bgg = MagicMock()
    client.fetch_thing_data = MagicMock()
    client.fetch_hot_items = MagicMock()
    return client


@pytest.fixture
@patch(
    "src.cogs.bgg_commands.BGGClient"
)  # Patch the BGGClient where it's imported in the cog
def bgg_cog(MockBGGClient, mock_bot, mock_bgg_client):
    """Fixture for the BggCommands cog with a mocked BGGClient."""
    # Replace the instance created in __init__ with our mock
    MockBGGClient.return_value = mock_bgg_client
    cog = BggCommands(bot=mock_bot)
    return cog


@pytest.mark.asyncio
async def test_bgg_info_id_query(bgg_cog, mock_context, mock_bgg_client):
    """Test the bgg_info command with a numeric ID query."""
    game_id_query = "12345"
    mock_game_data = {
        "id": game_id_query,
        "name": "Test Game",
        "year": "2023",
        "description": "A test description.",
        "image": "http://example.com/image.jpg",
        "stats": {
            "average": "8.5",
            "weight": "3.0",
            "users_rated": "100",
            "ranks": [{"name": "Overall", "value": "10"}],
        },
    }
    mock_bgg_client.fetch_thing_data.return_value = mock_game_data

    await bgg_cog.bgg_info.callback(bgg_cog, mock_context, query=game_id_query)

    mock_context.defer.assert_called_once()
    mock_bgg_client.fetch_thing_data.assert_called_once_with(game_id_query, stats=True)
    mock_context.send.assert_called_once()

    call_args, call_kwargs = mock_context.send.call_args
    embed = call_kwargs.get("embed")
    assert isinstance(embed, discord.Embed)
    assert embed.title == f"{mock_game_data['name']} ({mock_game_data['year']})"
    assert mock_game_data["description"] in embed.description
    assert embed.footer.text == f"BGG ID: {game_id_query}"
    assert len(embed.fields) > 0  # Check that some fields were added


@pytest.mark.asyncio
async def test_bgg_search(bgg_cog, mock_context, mock_bgg_client):
    """Test the bgg_search command."""
    search_query = "Search Term"
    mock_search_results = [
        {"id": "111", "name": "Game One", "year": "2021"},
        {"id": "222", "name": "Game Two", "year": None},  # Test game with no year
    ]
    mock_bgg_client.search_bgg.return_value = mock_search_results

    await bgg_cog.bgg_search.callback(bgg_cog, mock_context, query=search_query)

    mock_context.defer.assert_called_once()
    mock_bgg_client.search_bgg.assert_called_once_with(search_query)
    mock_context.send.assert_called_once()

    call_args, call_kwargs = mock_context.send.call_args
    response_text = call_args[0]
    assert (
        f"Found {len(mock_search_results)} game(s) matching '{search_query}'"
        in response_text
    )
    assert (
        f"1. {mock_search_results[0]['name']} ({mock_search_results[0]['year']}) - ID: `{mock_search_results[0]['id']}`"
        in response_text
    )
    assert (
        f"2. {mock_search_results[1]['name']}  - ID: `{mock_search_results[1]['id']}`"
        in response_text
    )  # Check formatting for no year
    assert "Use `!bgginfo <ID>`" in response_text


# Add more tests for bgg_hot, bgg_image etc. if desired
