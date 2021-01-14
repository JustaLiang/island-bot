#!/usr/bin/env python
# -*- coding: utf-8 -*-

import telegram as tg
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

from misc import parse_token, parse_name, parse_id
import numpy as np
import json, os, signal

ERR_REPLY = '請正確地使用指令喔^^'

# Functions
def string_sum(string):
    return sum([ ord(char) for char in string])

def string_hash(target, base):
    n = 13
    m = 1999
    target_sum = string_sum(target)
    base_sum = string_sum(base)
    return ((target_sum-base_sum)%m)**n%m

def determine(str_list, str_base, sort=False):
    str_hashs = [ string_hash(string, str_base) for string in str_list ]
    str_rank = sorted(dict(zip(str_list, str_hashs)).items(), key=lambda x:x[1])
    if sort:
        return ''.join(['\n%s (%.1f%%)'%(rank[0], 100-rank[1]/20) for rank in str_rank])
    else:
        return '%s (%.1f%%)'%(str_rank[0][0], 100-str_rank[0][1]/20)

def old_determine(str_list):
    str_mods = [ string_sum(string)%100 for string in str_list ]
    ttl_mod = sum(str_mods)%100
    min_diff = 100
    min_idx = 0
    for i,mod in enumerate(str_mods):
        diff = abs(mod - ttl_mod)
        if diff < min_diff:
            min_diff = diff 
            min_idx = i
    return str_list[min_idx]     

def split_question(str_list):
    whole_string = ' '.join(str_list)
    if '？' in whole_string:
        q_mark = '？'
    elif '?' in whole_string:
        q_mark = '?'
    else:
        return None, None
    qsn_opt = whole_string.split(q_mark)
    if len(qsn_opt) < 2 or qsn_opt[0] == '' or qsn_opt[1] == '':
        return None, None

    return qsn_opt[0], qsn_opt[1]

# Bot class
class CDInfoBot:
    def __init__(self, bot_token, bot_owner, bot_name):
        self.token = bot_token
        self.owner = bot_owner
        self.name = bot_name
        self.err_reply = ERR_REPLY
        self.envelope_state = False

        self.updater = Updater(self.token, use_context=True)
        dpr = self.updater.dispatcher
        dpr.add_handler(CommandHandler("start", self.start))
        dpr.add_handler(CommandHandler("choose", self.choose))
        dpr.add_handler(CommandHandler("random", self.random))
        dpr.add_handler(CommandHandler("tell", self.tell))
        dpr.add_handler(CommandHandler("tells", self.tells))
        dpr.add_handler(CommandHandler("shuffle", self.shuffle))
        dpr.add_handler(CommandHandler("pair", self.pair))
        dpr.add_handler(CommandHandler("dice", self.dice))
        dpr.add_handler(CommandHandler("sleep", self.sleep))
        dpr.add_handler(MessageHandler(Filters.all, self.show))
        dpr.add_handler(CallbackQueryHandler(self.envelope))
        print(f"[{self.name} ready]")

    def run(self):
        self.updater.start_polling(poll_interval=2, clean=True)
        print(f"[{self.name} running]")
        self.updater.idle()
        print(f"[{self.name} saving]")
        self._save_user_info()
        print(f"[{self.name} terminated]")

    def _valid_update(self, update):
        if update.message is None:
            return False
        else:
            print(update.message.from_user.full_name, ':', update.message.text)
            return True

    def _reply(self, update, content=None):
        if content is None:
            content = self.err_reply
        update.message.reply_text(content)
        print(self.name, ':', content)   

    # Handlers
    def start(self, update: Update, context: CallbackContext) -> None:
        update.message.reply_text("嗨？")

    def choose(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        if len(context.args) < 1:
            self._reply(update)
        else:
            result = old_determine(context.args)
            self._reply(update, result)

    def random(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        if len(context.args) < 1:
            self._reply(update)
        else:
            result = np.random.choice(context.args)
            self._reply(update, result)

    def tell(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        question, options = split_question(context.args)
        if question is None or options is None:
            self._reply(update)
            return
        options = options.split()
        if len(options) < 1:
            self._reply(update)
        else:
            result = determine(options, question)
            self._reply(update, result)

    def tells(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        question, options = split_question(context.args)
        if question is None or options is None:
            self._reply(update)
            return
        options = options.split()
        if len(options) < 1:
            self._reply(update)
        else:
            result = determine(options, question, sort=True)
            self._reply(update, result)    

    def shuffle(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        if len(context.args) < 1:
            self._reply(update)
        else:
            np.random.shuffle(context.args)
            result = ' '.join(context.args)
            self._reply(update, result)

    def pair(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return 
        source, target = split_question(context.args)
        if source is None or target is None:
            self._reply(update)
            return
        source = source.split()
        target = target.split()
        if len(source) <= len(target):
            np.random.shuffle(target)
        else:
            target = target * (len(source)//len(target)+1)
            np.random.shuffle(target)
        result = ''.join([ '\n'+src+' - '+tar for src,tar in zip(source, target)])
        self._reply(update, result)

    def show(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        if np.random.randint(0,25) == 0 and not self.envelope_state:
            self.envelope_state = True
            keyboard = [[tg.InlineKeyboardButton(callback_data=np.random.randint(10,31),text='領取')]]
            reply_markup = tg.InlineKeyboardMarkup(keyboard)
            update.message.bot.send_message(chat_id=update.message.chat_id, reply_markup=reply_markup, text="搶紅包囉！")

    def envelope(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        query.answer()
        if self.envelope_state:
            query.edit_message_text(f"{query.from_user.full_name} 收到{query.data}顆 島幣")
            self.envelope_state = False

    def dice(self, update: Update, context: CallbackContext) -> None:
        update.message.reply_dice(emoji=tg.constants.DICE_DICE)

    def dice_value(self, update: Update, context: CallbackContext) -> None:
        print(update.message.dice.value)

    def sleep(self, update: Update, context: CallbackContext) -> None:
        if update.message.from_user.id == self.owner:
            print(f"[{self.name} saving]")
            update.message.reply_text("zzz")
            print(f"[{self.name} terminated]")
            os.kill(os.getpid(), signal.SIGINT)

#-------------------------------------------------------------------
#   main
#-------------------------------------------------------------------
def main():

    bot_token = parse_token('token_CD_info_bot')
    if not bot_token:
        print("[bot token file not found]")
        return

    bot_owner = parse_id('id_justa')
    if not bot_owner:
        print("[owner id file not found]")
        return
    
    bot_name = 'Island Bot'

    bot = CDInfoBot(bot_token=bot_token,
                    bot_owner=bot_owner,
                    bot_name=bot_name)
    bot.run()

if __name__ == '__main__':
    main()