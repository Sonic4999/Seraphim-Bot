#!/usr/bin/env python3.7
from discord.ext import commands, flags
import discord, importlib
import datetime, humanize

import common.utils as utils

class OnCMDError(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def error_embed_generate(self, error_msg):
        error_embed = discord.Embed(
            colour = discord.Colour.red(),
            description = error_msg
        )

        return error_embed
            
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandInvokeError):
            original = error.original
            if not isinstance(original, discord.HTTPException):
                await utils.error_handle(self.bot, error, ctx)
        elif isinstance(error, flags.ArgumentParsingError):
            await ctx.reply(embed=self.error_embed_generate(str(error)))
        elif isinstance(error, commands.TooManyArguments):
            await ctx.reply(embed=self.error_embed_generate("You passed too many arguments to that command! Please make sure you're " +
            "passing in a valid argument/subcommand."))
        elif isinstance(error, commands.CommandOnCooldown):
            delta_wait = datetime.timedelta(seconds=error.retry_after)
            await ctx.reply(embed=self.error_embed_generate("You're doing that command too fast! " +
            f"Try again in `{humanize.precisedelta(delta_wait, format='%0.0f')}`."))
        elif isinstance(error, (commands.ConversionError, commands.UserInputError, commands.BadArgument)):
            await ctx.reply(embed=self.error_embed_generate(str(error)))
        elif isinstance(error, utils.CustomCheckFailure):
            await ctx.reply(embed=self.error_embed_generate(str(error)))
        elif isinstance(error, commands.CheckFailure):
            if ctx.guild != None:
                await ctx.reply(embed=self.error_embed_generate("You do not have the proper permissions to use that command."))
        elif isinstance(error, commands.CommandNotFound):
            pass
        else:
            await utils.error_handle(self.bot, error, ctx)

def setup(bot):
    importlib.reload(utils)
    bot.add_cog(OnCMDError(bot))