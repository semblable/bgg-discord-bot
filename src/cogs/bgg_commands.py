import discord
from discord.ext import commands
from typing import Optional
import re
import html
import json
from pathlib import Path

from ..bgg_api import BGGClient


class BggCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.USER_DATA_FILE = Path(__file__).parent.parent / "user_data.json"
        self._ensure_data_file_exists()
        self.bot = bot
        self.bgg = BGGClient()

    def _ensure_data_file_exists(self):
        """Creates the user data file if it doesn't exist."""
        if not self.USER_DATA_FILE.exists():
            with open(self.USER_DATA_FILE, "w") as f:
                json.dump({}, f)

    def _load_user_data(self) -> dict:
        """Loads the user data from the JSON file."""
        self._ensure_data_file_exists()
        try:
            with open(self.USER_DATA_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            # Return empty dict if file is corrupted or missing
            return {}

    def _save_user_data(self, data: dict):
        """Saves the user data to the JSON file."""
        self._ensure_data_file_exists()
        with open(self.USER_DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)

    def _clean_description(self, description: Optional[str]) -> str:
        """Removes HTML tags and decodes HTML entities from BGG descriptions."""
        if not description:
            return "No description available."
        desc = html.unescape(description)
        desc = re.sub("<[^<]+?>", "", desc)
        # Limit length for Discord embed display
        return (desc[:500] + "...") if len(desc) > 500 else desc

    @commands.hybrid_command(
        name="bgginfo", description="Get detailed information about a board game"
    )
    async def bgg_info(self, ctx: commands.Context, *, query: str):
        """Get detailed information about a board game from BGG using ID or search query."""
        await ctx.defer()
        try:
            game_id = None
            if query.isdigit():
                game_id = query
            else:
                results = self.bgg.search_bgg(query)
                if not results:
                    await ctx.send(
                        "No games found matching your search query.", ephemeral=True
                    )
                    return
                game_id = results[0]["id"] # Use the ID of the first search result

            if not game_id:
                await ctx.send(
                    "Could not determine a game ID from your query.", ephemeral=True
                )
                return

            game_data = self.bgg.fetch_thing_data(game_id, stats=True)

            embed = discord.Embed(
                title=f"{game_data.get('name', 'N/A')} ({game_data.get('year', 'N/A')})",
                description=self._clean_description(game_data.get("description")),
                color=discord.Color.blue(),
                url=f"https://boardgamegeek.com/boardgame/{game_data['id']}",
            )

            if game_data.get("image"):
                embed.set_thumbnail(url=game_data["image"])

            if game_data.get("stats"):
                stats = game_data["stats"]
                avg_rating = (
                    f"{float(stats.get('average', 0)):.2f}"
                    if stats.get("average")
                    else "N/A"
                )
                avg_weight = (
                    f"{float(stats.get('weight', 0)):.2f}"
                    if stats.get("weight")
                    else "N/A"
                )
                users_rated = stats.get("users_rated", "N/A")

                embed.add_field(name="Avg Rating", value=avg_rating, inline=True)
                embed.add_field(name="Weight", value=avg_weight, inline=True)
                embed.add_field(name="Users Rated", value=users_rated, inline=True)

                if stats.get("ranks"):
                    ranks_str = ""
                    for rank in stats["ranks"]:
                        if rank.get("value") and rank["value"] != "Not Ranked":
                            rank_name = (
                                rank.get("name", "Overall") # Use friendly name for rank type
                                .replace("boardgame", "")
                                .capitalize()
                            )
                            if not rank_name: # Handle empty name after replace
                                rank_name = "Overall"
                            ranks_str += f"{rank_name}: {rank['value']}\n"

                    if ranks_str:
                        embed.add_field(
                            name="Ranks", value=ranks_str.strip(), inline=False
                        )

            embed.set_footer(text=f"BGG ID: {game_data['id']}")
            await ctx.send(embed=embed)

        except Exception as e:
            print(f"Error in bgg_info: {e}")
            await ctx.send(
                f"An error occurred while fetching game info: {str(e)}", ephemeral=True
            )

    @commands.hybrid_command(
        name="bggsearch", description="Search for board games on BGG"
    )
    async def bgg_search(self, ctx: commands.Context, *, query: str):
        """Searches BGG for games matching the query."""
        await ctx.defer()
        try:
            results = self.bgg.search_bgg(query)
            if not results:
                await ctx.send("No games found matching your search.", ephemeral=True)
                return

            response_lines = [f"Found {len(results)} game(s) matching '{query}':"]
            for i, game in enumerate(results[:10]): # Limit to top 10 results
                year_str = f"({game['year']})" if game.get("year") else ""
                response_lines.append(
                    f"{i+1}. {game['name']} {year_str} - ID: `{game['id']}`"
                )

            if len(results) > 10:
                response_lines.append("\n(Showing top 10 results)")

            response_lines.append(
                "\nUse `!bgginfo <ID>` or `!bgginfo <Name>` for more details."
            )

            await ctx.send("\n".join(response_lines))

        except Exception as e:
            print(f"Error in bgg_search: {e}")
            await ctx.send(
                f"An error occurred during the search: {str(e)}", ephemeral=True
            )

    @commands.hybrid_command(
        name="bgghot",
        description="Show the current BGG Top 10 Hotness list with details",
    )
    async def bgg_hot(self, ctx: commands.Context):
        """Displays the current BGG Top 10 Hotness list with stats."""
        await ctx.defer()
        try:
            hot_items = self.bgg.fetch_hot_items()
            if not hot_items:
                await ctx.send(
                    "Could not retrieve the BGG Hotness list.", ephemeral=True
                )
                return

            top_10_items = hot_items[:10]

            embed = discord.Embed(
                title="BGG Board Game Hotness (Top 10)", color=discord.Color.orange()
            )

            description_lines = []
            for item in top_10_items:
                try:
                    detail_data = self.bgg.fetch_thing_data(item["id"], stats=True)
                    stats = detail_data.get("stats", {})
                    avg_rating = (
                        f"{float(stats.get('average', 0)):.2f}"
                        if stats.get("average")
                        else "N/A"
                    )
                    avg_weight = (
                        f"{float(stats.get('weight', 0)):.2f}"
                        if stats.get("weight")
                        else "N/A"
                    )

                    year_str = f"({item['year']})" if item.get("year") else ""
                    description_lines.append(
                        f"**{item['rank']}.** [{item['name']}](https://boardgamegeek.com/boardgame/{item['id']}) {year_str}\n"
                        f"   Rating: {avg_rating}, Weight: {avg_weight}"
                    )
                except Exception as detail_e:
                    # Log and continue if fetching details for one item fails
                    print(
                        f"Error fetching details for hot item {item['id']}: {detail_e}"
                    )
                    year_str = f"({item['year']})" if item.get("year") else ""
                    description_lines.append(
                        f"**{item['rank']}.** [{item['name']}](https://boardgamegeek.com/boardgame/{item['id']}) {year_str}\n"
                        f"   (Could not fetch details)"
                    )

            embed.description = "\n\n".join(description_lines)
            await ctx.send(embed=embed)

        except Exception as e:
            print(f"Error in bgg_hot: {e}")
            await ctx.send(
                f"An error occurred while fetching the hot list: {str(e)}",
                ephemeral=True,
            )

    @commands.hybrid_command(
        name="bggimage", description="Show the cover image for a board game"
    )
    async def bgg_image(self, ctx: commands.Context, *, query: str):
        """Displays the cover image for a game found by ID or search query."""
        await ctx.defer()
        try:
            game_id = None
            if query.isdigit():
                game_id = query
            else:
                results = self.bgg.search_bgg(query)
                if not results:
                    await ctx.send(
                        "No games found matching your search query.", ephemeral=True
                    )
                    return
                game_id = results[0]["id"] # Use the ID of the first search result

            if not game_id:
                await ctx.send(
                    "Could not determine a game ID from your query.", ephemeral=True
                )
                return

            game_data = self.bgg.fetch_thing_data(game_id, stats=False)

            if game_data.get("image"):
                embed = discord.Embed(
                    title=f"{game_data.get('name', 'N/A')} ({game_data.get('year', 'N/A')})",
                    color=discord.Color.green(),
                    url=f"https://boardgamegeek.com/boardgame/{game_data['id']}",
                )
                embed.set_image(url=game_data["image"])
                embed.set_footer(text=f"BGG ID: {game_data['id']}")
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"No image found for game ID {game_id}.", ephemeral=True)

        except Exception as e:
            print(f"Error in bgg_image: {e}")
            await ctx.send(
                f"An error occurred while fetching the game image: {str(e)}",
                ephemeral=True,
            )

    # --- User Favorites Commands --- #

    @commands.hybrid_group(name="bggfav", description="Manage your favorite BGG games")
    async def bggfav(self, ctx: commands.Context):
        """Group command for managing BGG favorites."""
        if ctx.invoked_subcommand is None:
            await ctx.send(
                "Invalid bggfav command. Use `add`, `remove`, or `list`.",
                ephemeral=True,
            )

    @bggfav.command(name="add", description="Add a game to your favorites list")
    async def bggfav_add(self, ctx: commands.Context, *, query: str):
        """Adds a game (by ID or name search) to your favorites."""
        await ctx.defer(ephemeral=True)
        user_id = str(ctx.author.id)
        game_id = None
        game_name = "Unknown Game"

        try:
            # Resolve query to game ID first
            if query.isdigit():
                game_id = query
                try: # Fetch name for confirmation message if ID provided
                    game_data = self.bgg.fetch_thing_data(game_id, stats=False)
                    game_name = game_data.get("name", game_name)
                except Exception:
                    await ctx.send(
                        f"Could not verify game ID '{query}'. Please ensure it's a valid BGG ID.",
                        ephemeral=True,
                    )
                    return
            else:
                results = self.bgg.search_bgg(query)
                if not results:
                    await ctx.send(
                        f"No games found matching '{query}'.", ephemeral=True
                    )
                    return
                game_id = results[0]["id"]
                game_name = results[0].get("name", game_name)

            if not game_id:
                await ctx.send(
                    "Could not determine a game ID from your query.", ephemeral=True
                )
                return

            user_data = self._load_user_data()
            if user_id not in user_data:
                user_data[user_id] = {"favorites": []}
            elif "favorites" not in user_data[user_id]:
                user_data[user_id]["favorites"] = []

            if game_id not in user_data[user_id]["favorites"]:
                user_data[user_id]["favorites"].append(game_id)
                self._save_user_data(user_data)
                await ctx.send(
                    f"Added '{game_name}' (ID: {game_id}) to your favorites.",
                    ephemeral=True,
                )
            else:
                await ctx.send(
                    f"'{game_name}' (ID: {game_id}) is already in your favorites.",
                    ephemeral=True,
                )

        except Exception as e:
            print(f"Error in bggfav_add: {e}")
            await ctx.send(
                f"An error occurred while adding the favorite: {str(e)}", ephemeral=True
            )

    @bggfav.command(name="remove", description="Remove a game from your favorites list")
    async def bggfav_remove(self, ctx: commands.Context, game_id: str):
        """Removes a game (by ID) from your favorites."""
        await ctx.defer(ephemeral=True)
        user_id = str(ctx.author.id)

        if not game_id.isdigit():
            await ctx.send(
                "Please provide the BGG Game ID (a number) to remove.", ephemeral=True
            )
            return

        try:
            user_data = self._load_user_data()

            if (
                user_id not in user_data
                or "favorites" not in user_data[user_id]
                or not user_data[user_id]["favorites"]
            ):
                await ctx.send(
                    "You don't have any favorites saved yet.", ephemeral=True
                )
                return

            if game_id in user_data[user_id]["favorites"]:
                user_data[user_id]["favorites"].remove(game_id)
                self._save_user_data(user_data)
                game_name = "Unknown Game"
                try: # Fetch name for confirmation message
                    game_data = self.bgg.fetch_thing_data(game_id, stats=False)
                    game_name = game_data.get("name", game_name)
                except Exception:
                    pass  # Ignore if fetching name fails, just use ID
                await ctx.send(
                    f"Removed '{game_name}' (ID: {game_id}) from your favorites.",
                    ephemeral=True,
                )
            else:
                await ctx.send(
                    f"Game ID '{game_id}' was not found in your favorites.",
                    ephemeral=True,
                )

        except Exception as e:
            print(f"Error in bggfav_remove: {e}")
            await ctx.send(
                f"An error occurred while removing the favorite: {str(e)}",
                ephemeral=True,
            )

    @bggfav.command(name="list", description="List your favorite games")
    async def bggfav_list(self, ctx: commands.Context):
        """Displays your saved favorite games."""
        await ctx.defer()  # Can take time to fetch details, so don't make ephemeral initially
        user_id = str(ctx.author.id)

        try:
            user_data = self._load_user_data()

            if (
                user_id not in user_data
                or "favorites" not in user_data[user_id]
                or not user_data[user_id]["favorites"]
            ):
                await ctx.send(
                    "You haven't added any favorite games yet. Use `!bggfav add <game>`.",
                    ephemeral=True,
                )
                return

            favorite_ids = user_data[user_id]["favorites"]
            if not favorite_ids:
                await ctx.send(
                    "You haven't added any favorite games yet. Use `!bggfav add <game>`.",
                    ephemeral=True,
                )
                return

            embed = discord.Embed(
                title=f"{ctx.author.display_name}'s Favorite Games",
                color=discord.Color.purple(),
            )

            description_lines = []
            fetch_errors = 0
            for i, game_id in enumerate(favorite_ids):
                try:
                    game_data = self.bgg.fetch_thing_data(game_id, stats=False)
                    game_name = game_data.get("name", f"ID: {game_id}")
                    game_year = game_data.get("year", "N/A")
                    description_lines.append(
                        f"{i+1}. [{game_name} ({game_year})](https://boardgamegeek.com/boardgame/{game_id}) - ID: `{game_id}`"
                    )
                except Exception as fetch_e:
                    print(
                        f"Error fetching details for favorite game ID {game_id}: {fetch_e}"
                    )
                    description_lines.append(
                        f"{i+1}. *Error fetching details for ID:* `{game_id}`"
                    )
                    fetch_errors += 1

            if (
                not description_lines
            ):  # Should not happen if favorite_ids is not empty, but safety check
                await ctx.send(
                    "Could not retrieve details for your favorites.", ephemeral=True
                )
                return

            embed.description = "\n".join(description_lines)
            if fetch_errors > 0:
                embed.set_footer(
                    text=f"Note: Could not fetch details for {fetch_errors} game(s)."
                )

            await ctx.send(embed=embed)

        except Exception as e:
            print(f"Error in bggfav_list: {e}")
            await ctx.send(
                f"An error occurred while listing favorites: {str(e)}", ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Required setup function for discord.py cogs."""
    await bot.add_cog(BggCommands(bot))
