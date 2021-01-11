#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

import telegram
from telegram import Update, constants
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

from misc import parse_token, parse_name
import numpy as np
import json, time

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

# Global variables
self_name = 'Island Bot'
token_file = 'token_CD_info_bot'

# user_json = {}

default_reply = "@@"

n = 13
m = 1999

# Functions
def mod_diff(mod1, mod2):
    if mod1 >= mod2:
        return min(mod1-mod2, mod2+m-mod1)
    else:
        return min(mod2-mod1, mod1+m-mod2)

def string_sum(string):
    return sum([ ord(char) for char in string])

def string_hash(target, base):
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

# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("嗨？")

def echo(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(update.message.text)

def certain_choose(update: Update, context: CallbackContext) -> None:
    if update.message is None:
        return
    print(parse_name(update.message.from_user), ':', update.message.text)

    options = update.message.text.split()

    if len(options) < 3:
        update.message.reply_text(default_reply)
        print(self_name, ':', default_reply)
    else:
        options = options[1:]
        result = old_determine(options)
        update.message.reply_text(result)
        print(self_name, ':', result)


def random_choose(update: Update, context: CallbackContext) -> None:
    if update.message is None:
        return
    print(parse_name(update.message.from_user), ':', update.message.text)

    options = update.message.text.split()

    if len(options) < 3:
        update.message.reply_text(default_reply)
        print(self_name, ':', default_reply)
    else:
        options = options[1:]
        which = np.random.randint(len(options))
        update.message.reply_text(options[which])
        print(self_name, ':', options[which])


def tell(update: Update, context: CallbackContext) -> None:
    if update.message is None:
        return
    print(parse_name(update.message.from_user), ':', update.message.text)

    if '？' in update.message.text:
        q_mark = '？'
    elif '?' in update.message.text:
        q_mark = '?'
    else:
        update.message.reply_text(default_reply)
        print(self_name, ':', default_reply)
        return

    qsn_opt = update.message.text.split(q_mark)

    qsn_str = qsn_opt[0].replace('/tell@CD_info_bot','').replace('/tell','').strip()
    options = qsn_opt[1].split()

    if len(options) < 1:
        update.message.reply_text(default_reply)
        print(self_name, ':', default_reply)
    else:
        result = determine(options, qsn_str)
        update.message.reply_text(result)
        print(self_name, ':', result)


def tells(update: Update, context: CallbackContext) -> None:
    if update.message is None:
        return
    print(parse_name(update.message.from_user), ':', update.message.text)

    if '？' in update.message.text:
        q_mark = '？'
    elif '?' in update.message.text:
        q_mark = '?'
    else:
        update.message.reply_text(default_reply)
        print(self_name, ':', default_reply)
        return

    qsn_opt = update.message.text.split(q_mark)

    qsn_str = qsn_opt[0].replace('/tells@CD_info_bot','').replace('/tells','').strip()
    options = qsn_opt[1].split()

    if len(options) < 1:
        update.message.reply_text(default_reply)
        print(self_name, ':', default_reply)
    else:
        result = determine(options, qsn_str, sort=True)
        update.message.reply_text(result)
        print(self_name, ':', result)    


def show(update: Update, context: CallbackContext) -> None:
    if update.message is None:
        return
    print(parse_name(update.message.from_user), ':', update.message.text)


def shuffle(update: Update, context: CallbackContext) -> None:
    if update.message is None:
        return
    print(parse_name(update.message.from_user), ':', update.message.text)

    options = update.message.text.split()

    if len(options) < 3:
        update.message.reply_text(default_reply)
        print(self_name, ':', default_reply)
    else:
        options = options[1:]
        np.random.shuffle(options)
        result = ' '.join(options)
        update.message.reply_text(result)
        print(self_name, ':', result)        


def pair(update: Update, context: CallbackContext) -> None:
    if update.message is None:
        return
    print(parse_name(update.message.from_user), ':', update.message.text)    

    if '？' in update.message.text:
        q_mark = '？'
    elif '?' in update.message.text:
        q_mark = '?'
    else:
        update.message.reply_text(default_reply)
        print(self_name, ':', default_reply)
        return

    source_target = update.message.text.split(q_mark)
    source = source_target[0].replace('/pair@CD_info_bot','').replace('/pair','').split()
    target = source_target[1].split()

    if len(source) <= len(target):
        np.random.shuffle(target)
    else:
        target = target * (len(source)//len(target)+1)

    result = ''.join([ '\n'+src+' - '+tar for src,tar in zip(source, target)])
    update.message.reply_text(result)
    print(self_name, ':', result)

def dice(update: Update, context: CallbackContext) -> None:
    update.message.reply_dice(emoji=constants.DICE_DICE)

def slot(update: Update, context: CallbackContext) -> None:
    update.message.reply_dice(emoji=constants.DICE_SLOT_MACHINE)

def fruit(update: Update, context: CallbackContext) -> None:
    keyboard = [[telegram.InlineKeyboardButton("蘋果", callback_data="蘋果"),
                 telegram.InlineKeyboardButton("香蕉", callback_data="香蕉")],
                [telegram.InlineKeyboardButton("橘子", callback_data="橘子"),
                 telegram.InlineKeyboardButton("芭樂", callback_data="芭樂")]]

    reply_markup = telegram.InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Please choose', reply_markup=reply_markup)

def fruit_button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    query.edit_message_text(text=f"你喜歡吃{query.data}")


#-------------------------------------------------------------------
#   main
#-------------------------------------------------------------------
def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    bot_token = parse_token(token_file)
    if bot_token:
        updater = Updater(bot_token, use_context=True)
    else:
        print("[token file not]")

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("choose", certain_choose))
    dispatcher.add_handler(CommandHandler("random", random_choose))
    dispatcher.add_handler(CommandHandler("tell", tell))
    dispatcher.add_handler(CommandHandler("tells", tells))
    dispatcher.add_handler(CommandHandler("shuffle", shuffle))
    dispatcher.add_handler(CommandHandler("pair", pair))
    dispatcher.add_handler(CommandHandler("dice", dice))
    dispatcher.add_handler(CommandHandler("slot", slot))
    dispatcher.add_handler(CommandHandler("fruit", fruit))
    dispatcher.add_handler(CallbackQueryHandler(fruit_button))

    # on noncommand i.e message - echo the message on Telegram
    # dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
    dispatcher.add_handler(MessageHandler(Filters.all, show))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()