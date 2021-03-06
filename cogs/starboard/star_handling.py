#!/usr/bin/env python3.7
from discord.ext import commands
import discord, importlib

import common.utils as utils
import common.star_utils as star_utils
import common.star_mes_handler as star_mes

class Star(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.star_task = bot.loop.create_task(self.starboard_queue())

    def cog_unload(self):
        self.star_task.cancel()

    async def starboard_queue(self):
        while True:
            entry = await self.bot.star_queue.get()

            chan = self.bot.get_channel(entry[0])
            starboard_entry = self.bot.starboard.get(entry[1])

            # if the channel and the entry for the message exists in the bot and if the entry is above or at the required amount
            # for that server
            if chan and starboard_entry and (len(starboard_entry.get_reactors()) >= self.bot.config[entry[2]]["star_limit"]
            or starboard_entry.forced):
                try:
                    mes = await chan.fetch_message(entry[1])
                    await star_mes.send(self.bot, mes)
                except discord.HTTPException: # you never know
                    pass

            self.bot.star_queue.task_done()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if not (star_utils.star_check(self.bot, payload) and str(payload.emoji) == "⭐"):
            return

        try:
            user, channel, mes = await utils.fetch_needed(self.bot, payload)
        except discord.Forbidden:
            return
        except discord.HTTPException:
            utils.msg_to_owner(self.bot, f"{payload.message_id}: could not find Message object. Channel: {payload.channel_id}")
            return

        if (not user.bot and not channel.id in self.bot.config[mes.guild.id]["star_blacklist"]):

            if mes.author.id != user.id:
                starboard_entry = self.bot.starboard.get(mes.id)

                if starboard_entry and (starboard_entry.frozen or starboard_entry.trashed):
                    return

                if not starboard_entry or not starboard_entry.star_var_id:
                    if channel.id != self.bot.config[mes.guild.id]["starboard_id"]:
                        await star_utils.modify_stars(self.bot, mes, payload.user_id, "ADD")
                        starboard_entry = self.bot.starboard.get(mes.id)
                        if not starboard_entry:
                            return

                        unique_stars = len(starboard_entry.get_reactors())

                        if unique_stars >= self.bot.config[mes.guild.id]["star_limit"]:
                            # the queue is infinite, so we should be good there
                            self.bot.star_queue.put_nowait((mes.channel.id, mes.id, mes.guild.id))
                                
                elif user.id != starboard_entry.author_id:
                    old_stars = len(starboard_entry.get_reactors())

                    await star_utils.modify_stars(self.bot, mes, payload.user_id, "ADD")

                    new_entry = self.bot.starboard.get(mes.id)
                    new_stars = len(new_entry.get_reactors())
                    if old_stars != new_stars: # we don't want to refresh too often
                        await star_utils.star_entry_refresh(self.bot, starboard_entry, mes.guild.id)

            elif self.bot.config[mes.guild.id]["remove_reaction"]:
                # the previous if confirms this is the author who is reaction (simply by elimination), so...
                try:
                    await mes.remove_reaction("⭐", mes.author)
                except discord.HTTPException:
                    pass
                except discord.InvalidArgument:
                    pass

    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if not (star_utils.star_check(self.bot, payload) and str(payload.emoji) == "⭐"):
            return
            
        try:
            user, channel, mes = await utils.fetch_needed(self.bot, payload)
        except discord.NotFound:
            return
        except discord.Forbidden:
            return

        if (not user.bot and mes.author.id != user.id
            and not channel.id in self.bot.config[mes.guild.id]["star_blacklist"]):

            star_variant = self.bot.starboard.get(mes.id)

            if star_variant and not (star_variant.frozen or star_variant.trashed):
                await star_utils.modify_stars(self.bot, mes, payload.user_id, "SUBTRACT")

                if star_variant.star_var_id:
                    await star_utils.star_entry_refresh(self.bot, star_variant, mes.guild.id)

    
    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        # So, okay, this is going to be a bit weird.
        # I need to use raw message edit because I want to make sure I don't need to rely on the cache...
        # but at the same time, this means I have 0 clue about what was exactly edited.
        # Suggesting a LOT can trigger this... trigger, this is not that great when we only want to know
        # if the message contents were update.
        # The best I can do is see if the raw data has the content in it, and just assume if it does,
        # that it means that it's a valid edit.

        if payload.data.get("content") != None:
            # So we passed that initial check, but now we actually need the message
            # (we could use the raw data, but better safe than sorry). Sometimes we might not
            # have to waste API calls on it, but sometimes we do.

            mes = payload.cached_message
            if not mes:
                chan = self.bot.get_channel(payload.channel_id)
                if chan:
                    try:
                        mes = await chan.fetch_message(payload.message_id)
                    except discord.HTTPException:
                        pass
            
            # if message exists and the edit message toggle is on
            if mes and self.bot.config[mes.guild.id]['star_edit_messages']:
                starboard_entry = self.bot.starboard.get(mes.id, check_for_var = True)

                # if the starboard entry exists and the star variant of the entry is not the message edited
                if starboard_entry and starboard_entry.star_var_id != mes.id:
                    new_embed = await star_mes.star_generate(self.bot, mes)

                    star_chan = mes.guild.get_channel(starboard_entry.starboard_id)
                    if star_chan:
                        try:
                            starboard_mes = await star_chan.fetch_message(starboard_entry.star_var_id)
                            starboard_content = starboard_mes.content
                            await starboard_mes.edit(content=starboard_content, embed=new_embed)
                        except discord.HTTPException:
                            pass

        
def setup(bot):
    importlib.reload(utils)
    importlib.reload(star_utils)
    importlib.reload(star_mes)
    
    bot.add_cog(Star(bot))
