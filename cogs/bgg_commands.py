import discord
from discord.ext import commands
from typing import Optional
import re # For cleaning description
import html # For unescaping HTML entities in description

# Correct the import path assuming bgg_api.py is in the root directory
from bgg_api import BGGClient

class BggCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bgg = BGGClient()

    def _clean_description(self, description: Optional[str]) -> str:
        """Removes HTML tags and decodes HTML entities from BGG descriptions."""
        if not description:
            return "No description available."
        # Decode HTML entities like & etc.
        desc = html.unescape(description)
        # Remove HTML tags
        desc = re.sub('<[^<]+?>', '', desc)
        # Limit length for Discord embed
        return (desc[:500] + '...') if len(desc) > 500 else desc

    @commands.hybrid_command(name="bgginfo", description="Get detailed information about a board game")
    async def bgg_info(self, ctx: commands.Context, *, query: str):
        """Get detailed information about a board game from BGG using ID or search query."""
        await ctx.defer() # Acknowledge interaction while fetching data
        try:
            game_id = None
            # First try to treat the query as an ID
            if query.isdigit():
                game_id = query
            else:
                # Search for the game
                results = self.bgg.search_bgg(query)
                if not results:
                    await ctx.send("No games found matching your search query.", ephemeral=True)
                    return
                # Use the ID of the first search result
                game_id = results[0]['id']

            if not game_id:
                 await ctx.send("Could not determine a game ID from your query.", ephemeral=True)
                 return

            # Get details for the game ID
            game_data = self.bgg.fetch_thing_data(game_id, stats=True)

            # Create embed with game info
            embed = discord.Embed(
                title=f"{game_data.get('name', 'N/A')} ({game_data.get('year', 'N/A')})",
                description=self._clean_description(game_data.get('description')),
                color=discord.Color.blue(),
                url=f"https://boardgamegeek.com/boardgame/{game_data['id']}" # Add link to BGG page
            )

            if game_data.get('image'):
                embed.set_thumbnail(url=game_data['image'])

            # Add stats if available
            if game_data.get('stats'):
                stats = game_data['stats']
                avg_rating = f"{float(stats.get('average', 0)):.2f}" if stats.get('average') else "N/A"
                avg_weight = f"{float(stats.get('weight', 0)):.2f}" if stats.get('weight') else "N/A"
                users_rated = stats.get('users_rated', 'N/A')

                embed.add_field(name="Avg Rating", value=avg_rating, inline=True)
                embed.add_field(name="Weight", value=avg_weight, inline=True)
                embed.add_field(name="Users Rated", value=users_rated, inline=True)

                # Add ranks if available
                if stats.get('ranks'):
                    ranks_str = ""
                    for rank in stats['ranks']:
                        if rank.get('value') and rank['value'] != 'Not Ranked':
                             # Use friendly name for rank type
                             rank_name = rank.get('name', 'Overall').replace('boardgame', '').capitalize()
                             if not rank_name: rank_name = "Overall" # Handle empty name after replace
                             ranks_str += f"{rank_name}: {rank['value']}\n"

                    if ranks_str:
                        embed.add_field(name="Ranks", value=ranks_str.strip(), inline=False)

            embed.set_footer(text=f"BGG ID: {game_data['id']}")
            await ctx.send(embed=embed)

        except Exception as e:
            print(f"Error in bgg_info: {e}") # Log error for debugging
            await ctx.send(f"An error occurred while fetching game info: {str(e)}", ephemeral=True)

    @commands.hybrid_command(name="bggsearch", description="Search for board games on BGG")
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
                year_str = f"({game['year']})" if game.get('year') else ""
                response_lines.append(f"{i+1}. {game['name']} {year_str} - ID: `{game['id']}`")

            if len(results) > 10:
                response_lines.append("\n(Showing top 10 results)")

            response_lines.append("\nUse `!bgginfo <ID>` or `!bgginfo <Name>` for more details.")

            await ctx.send("\n".join(response_lines))

        except Exception as e:
            print(f"Error in bgg_search: {e}")
            await ctx.send(f"An error occurred during the search: {str(e)}", ephemeral=True)

    @commands.hybrid_command(name="bgghot", description="Show the current BGG Top 10 Hotness list with details")
    async def bgg_hot(self, ctx: commands.Context):
        """Displays the current BGG Top 10 Hotness list with stats."""
        await ctx.defer()
        try:
            hot_items = self.bgg.fetch_hot_items()
            if not hot_items:
                await ctx.send("Could not retrieve the BGG Hotness list.", ephemeral=True)
                return

            top_10_items = hot_items[:10] # Get only the top 10

            embed = discord.Embed(
                title="BGG Board Game Hotness (Top 10)",
                color=discord.Color.orange()
            )

            description_lines = []
            for item in top_10_items:
                try:
                    # Fetch detailed stats for each hot item
                    detail_data = self.bgg.fetch_thing_data(item['id'], stats=True)
                    stats = detail_data.get('stats', {})
                    avg_rating = f"{float(stats.get('average', 0)):.2f}" if stats.get('average') else "N/A"
                    avg_weight = f"{float(stats.get('weight', 0)):.2f}" if stats.get('weight') else "N/A"

                    year_str = f"({item['year']})" if item.get('year') else ""
                    description_lines.append(
                        f"**{item['rank']}.** [{item['name']}](https://boardgamegeek.com/boardgame/{item['id']}) {year_str}\n"
                        f"   Rating: {avg_rating}, Weight: {avg_weight}"
                    )
                except Exception as detail_e:
                    # Handle cases where fetching details for a specific hot item fails
                    print(f"Error fetching details for hot item {item['id']}: {detail_e}")
                    year_str = f"({item['year']})" if item.get('year') else ""
                    description_lines.append(
                         f"**{item['rank']}.** [{item['name']}](https://boardgamegeek.com/boardgame/{item['id']}) {year_str}\n"
                         f"   (Could not fetch details)"
                    )


            embed.description = "\n\n".join(description_lines) # Add extra newline for spacing
            await ctx.send(embed=embed)

        except Exception as e:
            print(f"Error in bgg_hot: {e}")
            await ctx.send(f"An error occurred while fetching the hot list: {str(e)}", ephemeral=True)

    @commands.hybrid_command(name="bggimage", description="Show the cover image for a board game")
    async def bgg_image(self, ctx: commands.Context, *, query: str):
        """Displays the cover image for a game found by ID or search query."""
        await ctx.defer()
        try:
            game_id = None
            # First try to treat the query as an ID
            if query.isdigit():
                game_id = query
            else:
                # Search for the game
                results = self.bgg.search_bgg(query)
                if not results:
                    await ctx.send("No games found matching your search query.", ephemeral=True)
                    return
                # Use the ID of the first search result
                game_id = results[0]['id']

            if not game_id:
                 await ctx.send("Could not determine a game ID from your query.", ephemeral=True)
                 return

            # Get details for the game ID (don't need stats for image)
            game_data = self.bgg.fetch_thing_data(game_id, stats=False)

            if game_data.get('image'):
                embed = discord.Embed(
                    title=f"{game_data.get('name', 'N/A')} ({game_data.get('year', 'N/A')})",
                    color=discord.Color.green(),
                    url=f"https://boardgamegeek.com/boardgame/{game_data['id']}"
                )
                embed.set_image(url=game_data['image'])
                embed.set_footer(text=f"BGG ID: {game_data['id']}")
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"No image found for game ID {game_id}.", ephemeral=True)

        except Exception as e:
            print(f"Error in bgg_image: {e}")
            await ctx.send(f"An error occurred while fetching the game image: {str(e)}", ephemeral=True)


# Setup function required by discord.py to load the cog
async def setup(bot: commands.Bot):
    await bot.add_cog(BggCommands(bot))