#!/usr/bin/env python3.7
from discord.ext import commands
from discord.ext.commands.errors import BadArgument
import traceback, discord, datetime, re
from pathlib import Path

async def proper_permissions(ctx):
    permissions = ctx.author.guild_permissions
    return (permissions.administrator or permissions.manage_guild)

async def fetch_needed(bot, payload):
    guild = await bot.fetch_guild(payload.guild_id)
    user = await guild.fetch_member(payload.user_id)

    channel = await bot.fetch_channel(payload.channel_id)
    mes = await channel.fetch_message(payload.message_id)

    return user, channel, mes

async def error_handle(bot, error, ctx = None):
    error_str = ''.join(traceback.format_exception(etype=type(error), value=error, tb=error.__traceback__))

    await msg_to_owner(bot, error_str)

    if ctx != None:
        await ctx.send("An internal error has occured. The bot owner has been notified.")

async def msg_to_owner(bot, string):
    application = await bot.application_info()
    owner = application.owner

    str_chunks = [string[i:i+1950] for i in range(0, len(string), 1950)]

    for chunk in str_chunks:
        await owner.send(f"{chunk}")

async def user_from_id(bot, guild, user_id):
    user = guild.get_member(user_id)
    if user == None:
        try:
            user = await bot.fetch_user(user_id)
        except discord.NotFound:
            user = None

    return user

def file_to_ext(str_path, start_path):
    str_path = str_path.replace(start_path, "")
    str_path = str_path.replace("/", ".")
    return str_path.replace(".py", "")

def get_all_extensions(filename):
    ext_files = []
    loc_split = filename.split("cogs")
    start_path = loc_split[0]

    if start_path == filename:
        start_path = start_path.replace("main.py", "")
    start_path = start_path.replace("\\", "/")

    if start_path[-1] != "/":
        start_path += "/"

    pathlist = Path(f"{start_path}/cogs").glob('**/*.py')
    for path in pathlist:
        str_path = str(path.as_posix())
        str_path = file_to_ext(str_path, start_path)

        if str_path != "cogs.db_handler":
            ext_files.append(str_path)

    return ext_files

class TimeDurationConverter(commands.Converter):
    # Converts a string to a time duration.

    convert_dict = {
        "s": 1,
        "second": 1,
        "seconds": 1,

        "m": 60,
        "minute": 60,
        "minutes": 60,

        "h": 3600,
        "hour": 3600,
        "hours": 3600,

        "d": 86400, # h * 24
        "day": 86400,
        "days": 86400,

        "mo": 2592000, # d * 30
        "month": 2592000,
        "months": 2592000,

        "y": 31536000, # d * 365
        "year": 31536000,
        "years": 31536000
    }
    regex = re.compile(r"([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))(?:[eE]([+-]?\d+))?")

    def to_seconds(self, time_value, time_prefix):
        try:
            return self.convert_dict[time_prefix] * time_value
        except KeyError:
            raise BadArgument(f"{time_prefix} is not a valid time prefix.")

    async def convert(self, ctx, argument):
        time_value_list = []
        time_format_list = []
        time_span = -1

        for match in self.regex.finditer(argument):
            time_value_list.append(float(match.group()))

        for entry in self.regex.split(argument):
            if not (entry == "" or entry == None):
                time_format_list.append(entry.strip().lower())

        if (time_format_list == [] or time_value_list == [] 
            or len(time_format_list) != len(time_value_list)):
            raise BadArgument(f"1. Argument {argument} is not a valid time duration.\n" +
            f"{time_format_list}, {time_value_list}")

        for i in range(len(time_format_list)):
            if time_span == -1:
                time_span = 0

            time_span += self.to_seconds(time_value_list[i], time_format_list[i])

        if time_span == -1:
            raise BadArgument(f"2. Argument {argument} is not a valid time duration.\n" +
            f"{time_format_list}, {time_value_list}")

        return datetime.timedelta(seconds=time_span)