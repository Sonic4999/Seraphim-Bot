from discord.ext import commands
import discord, datetime
import importlib, humanize

import common.utils as utils
import common.fuzzys as fuzzys
import common.paginator as paginator

class PingRoleCMDs(commands.Cog, name="Pingable Roles"):
    """Commands for pingable roles. If you wish to add a pingable role, please view the settings command."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases = ["pingrole", "roleping", "role_ping"])
    async def ping_role(self, ctx, *, role_obj: fuzzys.FuzzyRoleConverter):
        """Pings the role specified if the role isn't on cooldown and has been added to a list."""

        ping_roles = self.bot.config[ctx.guild.id]["pingable_roles"]

        if ping_roles == {}:
            raise utils.CustomCheckFailure("There are no roles for you to ping!")

        if not str(role_obj.id) in ping_roles.keys():
            raise commands.BadArgument("That role isn't pingable!")

        role_entry = ping_roles[str(role_obj.id)]

        now = datetime.datetime.utcnow()
        time_period = datetime.timedelta(seconds=role_entry["time_period"])
        last_used = datetime.datetime.utcfromtimestamp(role_entry["last_used"])
        next_use = last_used + time_period

        if now < next_use:
            till_next_time = next_use - now
            time_text = humanize.precisedelta(till_next_time, format='%0.0f')
            raise utils.CustomCheckFailure(f"You cannot ping that role yet! Please wait: `{time_text}` before trying to ping the role again.")
        else:
            await ctx.reply(role_obj.mention, allowed_mentions=discord.AllowedMentions(roles=True))

            self.bot.config[ctx.guild.id]["pingable_roles"][str(role_obj.id)]["last_used"] = now.timestamp()

    @commands.command(aliases = ["list_ping_roles", "list_pingroles", "pingroles",
    "list_rolepings", "rolepings", "list_role_pings", "role_pings"])
    async def ping_roles(self, ctx):
        """Returns a list of roles that have been made pingable and their cooldown."""
        ping_roles = ctx.bot.config[ctx.guild.id]["pingable_roles"]

        if ping_roles == {}:
            raise utils.CustomCheckFailure("There are no roles added!")

        role_list = []

        for role in ping_roles.keys():
            role_obj = ctx.guild.get_role(int(role))

            if role_obj != None:
                period_delta = datetime.timedelta(seconds=ping_roles[role]['time_period'])
                time_text = None

                now = datetime.datetime.utcnow()
                last_used = datetime.datetime.utcfromtimestamp(ping_roles[role]["last_used"])
                next_use = last_used + period_delta

                if now < next_use:
                    till_next_time = next_use - now
                    time_text = humanize.precisedelta(till_next_time, format='%0.1f')

                if time_text:
                    role_list.append((role_obj.name, f"{humanize.precisedelta(period_delta, format='%0.1f')} cooldown\n{time_text} until next use"))
                else:
                    role_list.append((role_obj.name, f"{humanize.precisedelta(period_delta, format='%0.1f')} cooldown"))

            else:
                del ctx.bot.config[ctx.guild.id]["pingable_roles"][role]

        if role_list != []:
            to_pag = paginator.FieldPages(ctx, entries=role_list)
            await to_pag.paginate()
        else:
            raise utils.CustomCheckFailure("There are no roles added!")

def setup(bot):
    importlib.reload(utils)
    importlib.reload(fuzzys)
    importlib.reload(paginator)

    bot.add_cog(PingRoleCMDs(bot))
