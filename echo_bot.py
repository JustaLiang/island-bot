#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=W0613, C0116
# type: ignore[union-attr]
# This program is dedicated to the public domain under the CC0 license.

"""
Simple Bot to reply to Telegram messages.
First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging

from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

TOKEN = '1415640092:AAGjpSpqw0wLFUiy-mw4Mi9IoPNelsxV8YQ'

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

def random_choose(str_list):
    str_sum = [ sum([ord(char) for char in string]) for string in str_list ]
    f_order = [ s%100 for s in str_sum ]
    s_order = [ s%1000 for s in str_sum ]

    max_i = 0
    for i in range(len(str_list)):
        if (f_order[i] > f_order[max_i]) or (f_order[i] == f_order[max_i] and s_order[i] > s_order[max_i]):
            max_v = f_order[i]
            max_i = i
    return str_list[max_i]

# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    update.message.reply_text("嗨！")


def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text("7414")


def echo(update: Update, context: CallbackContext) -> None:
    """Echo the user message."""
    update.message.reply_text(update.message.text)


def choose(update: Update, context: CallbackContext) -> None:
    """choose what to eat."""
    options = update.message.text.split()
    if len(options) <= 1:
        update.message.reply_text("要選什麼？來亂的逆？")
    elif len(options) == 2:
        update.message.reply_text("幹，只有一個要選三小？")
    else:
        options = options[1:]
        # which = len(update.message.text)%len(options)
        update.message.reply_text(random_choose(options))


def show(update: Update, context: CallbackContext) -> None:
    """Echo the user message."""
    try:
        print(update.message.text)
    except:
        return


def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("choose", choose))

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