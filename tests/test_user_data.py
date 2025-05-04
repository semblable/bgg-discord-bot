import pytest
import discord
from discord.ext import commands
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
import json
from pathlib import Path

# Adjust the import path based on the project structure
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
    ctx.author.id = 123456789  # Consistent test user ID
    ctx.author.display_name = "TestUser"
    return ctx


@pytest.fixture
def mock_bgg_client():
    """Fixture for a mocked BGGClient."""
    client = MagicMock(spec=BGGClient)
    client.search_bgg = MagicMock()
    client.fetch_thing_data = MagicMock()
    return client


@pytest.fixture
@patch("src.cogs.bgg_commands.BGGClient")
def bgg_cog(MockBGGClient, mock_bot, mock_bgg_client):
    """Fixture for the BggCommands cog with a mocked BGGClient."""
    MockBGGClient.return_value = mock_bgg_client
    cog = BggCommands(bot=mock_bot)
    # Mock the path resolution for consistency in tests
    cog.USER_DATA_FILE = Path("/fake/path/user_data.json")
    return cog


@pytest.mark.asyncio
@patch("src.cogs.bgg_commands.Path.exists")  # Mock Path.exists
@patch("builtins.open", new_callable=mock_open)  # Mock open globally
@patch("json.load")
@patch("json.dump")
async def test_bggfav_add_new_user(
    mock_json_dump,
    mock_json_load,
    mock_open_func,
    mock_path_exists,
    bgg_cog,
    mock_context,
    mock_bgg_client,
):
    """Test adding a favorite for a user not previously in the data file."""
    mock_path_exists.return_value = True  # Assume file exists
    mock_json_load.return_value = {}  # Start with empty data
    game_id_to_add = "9876"
    game_name = "Favorite Game"
    mock_bgg_client.fetch_thing_data.return_value = {
        "id": game_id_to_add,
        "name": game_name,
    }

    # Call the callback directly, passing self (the cog instance)
    await bgg_cog.bggfav_add.callback(bgg_cog, mock_context, query=game_id_to_add)

    mock_context.defer.assert_called_once_with(ephemeral=True)
    mock_bgg_client.fetch_thing_data.assert_called_once_with(
        game_id_to_add, stats=False
    )
    mock_json_load.assert_called_once()  # Called by _load_user_data
    # Check that save was called with the correct data structure
    expected_data = {str(mock_context.author.id): {"favorites": [game_id_to_add]}}
    mock_json_dump.assert_called_once()
    call_args, call_kwargs = mock_json_dump.call_args
    assert call_args[0] == expected_data
    # Check file handle in dump call
    assert call_args[1] == mock_open_func()

    mock_context.send.assert_called_once_with(
        f"Added '{game_name}' (ID: {game_id_to_add}) to your favorites.", ephemeral=True
    )


@pytest.mark.asyncio
@patch("src.cogs.bgg_commands.Path.exists")
@patch("builtins.open", new_callable=mock_open)
@patch("json.load")
@patch("json.dump")
async def test_bggfav_remove(
    mock_json_dump,
    mock_json_load,
    mock_open_func,
    mock_path_exists,
    bgg_cog,
    mock_context,
    mock_bgg_client,
):
    """Test removing a favorite."""
    user_id = str(mock_context.author.id)
    game_id_to_remove = "5555"
    other_game_id = "1111"
    game_name = "Game To Remove"
    initial_data = {user_id: {"favorites": [other_game_id, game_id_to_remove]}}

    mock_path_exists.return_value = True
    mock_json_load.return_value = initial_data
    mock_bgg_client.fetch_thing_data.return_value = {
        "id": game_id_to_remove,
        "name": game_name,
    }  # For confirmation message

    # Call the callback directly
    await bgg_cog.bggfav_remove.callback(
        bgg_cog, mock_context, game_id=game_id_to_remove
    )

    mock_context.defer.assert_called_once_with(ephemeral=True)
    mock_json_load.assert_called_once()
    # Check saved data
    expected_data = {user_id: {"favorites": [other_game_id]}}
    mock_json_dump.assert_called_once()
    call_args, call_kwargs = mock_json_dump.call_args
    assert call_args[0] == expected_data

    mock_bgg_client.fetch_thing_data.assert_called_once_with(
        game_id_to_remove, stats=False
    )  # Called for name
    mock_context.send.assert_called_once_with(
        f"Removed '{game_name}' (ID: {game_id_to_remove}) from your favorites.",
        ephemeral=True,
    )


# Add tests for edge cases: removing non-existent ID, listing empty favorites, file not found initially etc.
