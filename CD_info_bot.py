#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=W0613, C0116

import logging

from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

from misc import parse_token, parse_name
import numpy as np

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

# Global variables
self_name = 'Island Bot'
token_file = 'token_CD_info_bot'

# Functions
def string_ord(string):
    return sum([ ord(char) for char in string ])

def determine(str_list):
    str_sum = [ string_ord(string) for string in str_list ]
    str_mod = [ s%100 for s in str_sum ]
    ttl_mod = sum(str_mod)%100

    min_diff = 100
    min_idx = 0
    for i,mod in enumerate(str_mod):
        diff = abs(mod - ttl_mod)
        if diff < min_diff:
            min_diff = diff
            min_idx = i

    return str_list[min_idx]


# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    update.message.reply_text("嗨？")

def echo(update: Update, context: CallbackContext) -> None:
    """Echo the user message."""
    update.message.reply_text(update.message.text)

def certain_choose(update: Update, context: CallbackContext) -> None:

    print(parse_name(update.message.from_user), ':', update.message.text)

    try:
        options = update.message.text.split()
    except:
        print('[split error]')
        pass

    if len(options) <= 2:
        update.message.reply_text('？？？')
        print(self_name, ': ？？？')
    else:
        options = options[1:]
        result = determine(options)
        update.message.reply_text(result)
        print(self_name, ':', result)

def random_choose(update: Update, context: CallbackContext) -> None:

    print(parse_name(update.message.from_user), ':', update.message.text)

    try:
        options = update.message.text.split()
    except:
        print('[split error]')
        pass

    if len(options) <= 2:
        update.message.reply_text('？？？')
        print(self_name, ': ？？？')

    else:
        options = options[1:]
        which = np.random.randint(len(options))
        update.message.reply_text(options[which])
        print(self_name, ':', options[which])

def show(update: Update, context: CallbackContext) -> None:
    """Echo the user message."""
    try:
        print(parse_name(update.message.from_user), ':', update.message.text)
    except:
        print("[display error]")
        pass

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

    # on noncommand i.e message - echo the message on Telegram
    # dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, show))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()