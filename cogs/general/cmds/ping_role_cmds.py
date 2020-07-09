from discord.ext import commands
import discord, datetime
import importlib, humanize

import common.utils as utils

class PingRoleCMDs(commands.Cog, name="Pingable Roles"):
    """Commands for pingable roles. If you wish to add a pingable role, please view the settings command."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases = ["pingrole", "roleping", "role_ping"])
    async def ping_role(self, ctx, *, role_name):
        """Pings the role specified if the role isn't on cooldown and has been added to a list."""

        ping_roles = self.bot.config[ctx.guild.id]["pingable_roles"]

        if ping_roles == {}:
            await ctx.send("There are no roles for you to ping!")
            return

        role_obj = None

        for role in ctx.guild.roles:
            if role.name.lower() == role_name.lower():
                role_obj = role

        if role_obj == None:
            await ctx.send("That role doesn't exist!")
            return
        if not str(role_obj.id) in ping_roles.keys():
            await ctx.send("That role isn't pingable!")
            return

        role_entry = ping_roles[str(role_obj.id)]

        now = datetime.datetime.utcnow()
        time_period = datetime.timedelta(seconds=role_entry["time_period"])
        last_used = datetime.datetime.utcfromtimestamp(role_entry["last_used"])
        next_use = last_used + time_period

        if now < next_use:
            till_next_time = next_use - now
            time_text = humanize.precisedelta(till_next_time)
            await ctx.send(f"You cannot ping that role yet! Please wait: `{time_text}` before trying to ping the role again.")
            return
        else:
            await role_obj.edit(mentionable=True)
            await ctx.send(role_obj.mention)
            await role_obj.edit(mentionable=False)

            self.bot.config[ctx.guild.id]["pingable_roles"][str(role_obj.id)]["last_used"] = now.timestamp()

    @commands.command(aliases = ["list_ping_roles", "list_pingroles", "pingroles",
    "list_rolepings", "rolepings", "list_role_pings", "role_pings"])
    async def ping_roles(self, ctx):
        """Returns a list of roles that have been made pingable and their cooldown."""
        ping_roles = ctx.bot.config[ctx.guild.id]["pingable_roles"]

        if ping_roles == {}:
            await ctx.send("There are no roles added!")
            return

        role_list = []

        for role in ping_roles.keys():
            role_obj = ctx.guild.get_role(int(role))
            period_delta = datetime.timedelta(seconds=ping_roles[role]['time_period'])

            if role_obj != None:
                role_list.append(f"`{role_obj.name}, {humanize.precisedelta(period_delta, format='%0.0f')} cooldown`")
            else:
                del ctx.bot.config[ctx.guild.id]["pingable_roles"][role]

        if role_list != []:
            role_str = ", ".join(role_list)
            await ctx.send(f"Pingable roles: {role_str}")
        else:
            await ctx.send("There are no roles added!")

def setup(bot):
    importlib.reload(utils)
    bot.add_cog(PingRoleCMDs(bot))
