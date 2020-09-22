from discord.ext import commands, flags
import discord, importlib, typing
import os, datetime

import common.utils as utils
import common.image_utils as image_utils

class HelperCMDs(commands.Cog, name = "Helper"):
    """A series of commands made for tasks that are usually difficult to do, especially on mobile."""
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.check(utils.proper_permissions)
    async def restore_roles(self, ctx, member: discord.Member):
        """Restores the roles a user had before leaving, suggesting they left less than 15 minutes ago.
        The user running this command must have Manage Server permissions.
        Useful for... accidential leaves? Troll leaves? Yeah, not much, but Despair's Horizon wanted it."""

        member_entry = self.bot.role_rolebacks.get(member.id)
        if member_entry == None:
            raise commands.BadArgument("That member did not leave in the last 15 minutes!")

        now = datetime.datetime.utcnow()
        fifteen_prior = now - datetime.timedelta(minutes=15)
        
        if member_entry["time"] < fifteen_prior:
            del self.bot.role_rolebacks[member_entry["id"]]
            raise commands.BadArgument("That member did not leave in the last 15 minutes!")

        top_role = ctx.guild.me.top_role
        unadded_roles = []
        added_roles = []

        for role in member_entry["roles"]:
            if role.is_default():
                continue
            elif role > top_role or not role in ctx.guild.roles:
                unadded_roles.append(role)
            elif role in member.roles:
                continue
            else:
                added_roles.append(role)

        if added_roles:
            try:
                await member.add_roles(*added_roles, reason=f"Restoring old roles: done by {str(ctx.author)}.", atomic=False)
            except discord.HTTPException as error:
                await ctx.send("Something happened while trying to restore the roles this user had.\n" +
                "This shouldn't be happening, and this should have been caught earlier by the bot. Try contacting the bot owner about it.\n" +
                f"Error: {error}")
                return
        else:
            raise commands.BadArgument("There were no roles to restore for this user!")
        
        del self.bot.role_rolebacks[member_entry["id"]]

        final_msg = []
        final_msg.append(f"Roles restored: `{','.join([r.name for r in added_roles])}``.")
        if unadded_roles:
            final_msg.append(f"Roles not restored: `{','.join([r.name for r in unadded_roles])}`. " +
            "This was most likely because these roles are higher than the bot's own role or the roles no longer exist.")

        await ctx.send("\n\n".join(unadded_roles), allowed_mentions=utils.deny_mentions(ctx.author))

    @commands.command(aliases=["togglensfw"])
    @commands.check(utils.proper_permissions)
    async def toggle_nsfw(self, ctx, channel: typing.Optional[discord.TextChannel]):
        """Toggles either the provided channel or the channel the command is used it on or off NSFW mode.
        Useful for mobile devices, which for some reason cannot do this."""

        if channel == None:
            channel = ctx.channel

        toggle = not channel.is_nsfw()

        try:
            await channel.edit(nsfw = toggle)
            await ctx.send(f"{channel.mention}'s' NSFW mode has been set to: {toggle}.")
        except discord.HTTPException as e:
            await ctx.send("".join(
                    ("I was unable to change this channel's NSFW mode! This might be due to me not having the ",
                    "permissions to or some other weird funkyness with Discord. Maybe this error will help you.\n",
                    f"Error: {e}")
                )
            )
            return

    @commands.command(aliases=["addemoji"])
    @commands.check(utils.proper_permissions)
    async def add_emoji(self, ctx, emoji_name, emoji: typing.Union[image_utils.URLToImage, discord.PartialEmoji, None]):
        """Adds the URL, emoji, or image given as an emoji to this server.
        If it's an URL or image, it must be of type GIF, JPG, or PNG. It must also be under 256 KB.
        If it's an emoji, it must not already be on the server the command is being used in.
        The name must be at least 2 characters.
        Useful if you're on iOS and transparency gets the best of you, you want to add an emoji from a URL, or
        you want to... take an emoji from another server."""

        if len(emoji_name) < 2:
            raise commands.BadArgument("Emoji name must at least 2 characters!")

        if emoji == None:
            url = image_utils.image_from_ctx(ctx)
        elif isinstance(emoji, discord.PartialEmoji):
            possible_emoji = self.bot.get_emoji(emoji.id)
            if possible_emoji != None and possible_emoji.guild_id == ctx.guild.id:
                raise commands.BadArgument("This emoji already exists here!")
            else:
                url = str(emoji.url)
        else:
            url = emoji

        emoji_count = len(ctx.guild.emojis)
        if emoji_count >= ctx.guild.emoji_limit:
            raise utils.CustomCheckFailure("This guild has no more emoji slots!")

        async with ctx.channel.typing():
            emoji_data = await image_utils.get_file_bytes(url, 262144, equal_to=False) # 256 KiB, which I assume Discord uses

            try:
                emoji = await ctx.guild.create_custom_emoji(name=emoji_name, image=emoji_data, reason=f"Created by {str(ctx.author)}")
            except discord.HTTPException as e:
                await ctx.send("".join(
                        ("I was unable to add this emoji! This might be due to me not having the ",
                        "permissions or the name being improper in some way. Maybe this error will help you.\n",
                        f"Error: {e}")
                    )
                )
                return
            finally:
                del emoji_data

            await ctx.send(f"Added {str(emoji)}!")

    @commands.command(aliases=["getemojiurl"])
    async def get_emoji_url(self, ctx, emoji: typing.Union[discord.PartialEmoji, str]):
        """Gets the emoji URL from an emoji.
        The emoji does not have to be from the server it's used in, but it does have to be an emoji, not a name or URL."""

        if isinstance(emoji, str):
            raise commands.BadArgument("The argument provided is not a custom emoji!")

        if emoji.is_custom_emoji():
            await ctx.send(f"URL: {str(emoji.url)}")
        else:
            # this shouldn't happen due to how the PartialEmoji converter works, but you never know
            raise commands.BadArgument("This emoji is not a custom emoji!")

    @commands.command()
    @commands.check(utils.proper_permissions)
    async def publish(self, ctx, msg: discord.Message):
        """Publishes a message in a news channel. Useful if you're on mobile.
        The message either needs to be a message ID of a message in the channel the command is being run in,
        a {channel id}-{message id} format, or the message link itself.
        Both you and the bot need Manage Server permissions to use this."""

        if msg.channel.type != discord.ChannelType.news:
            raise commands.BadArgument("This channel isn't a news channel!")
        elif not msg.channel.permissions_for(ctx.guild.me).manage_messages:
            raise utils.CustomCheckFailure("I do not have the proper permissions to do that!")

        try:
            await msg.publish()
            await ctx.send("Published!")
        except discord.HTTPException as e:
            await ctx.send(f"An error occured. This shouldn't happen, but here's the error (it might be useful to you): {e}")

def setup(bot):
    importlib.reload(utils)
    importlib.reload(image_utils)
    
    bot.add_cog(HelperCMDs(bot))