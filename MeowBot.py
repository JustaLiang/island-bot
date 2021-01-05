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

import numpy as np
import json
import logging

from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

from parse_token import parse_token

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

def parse_name(name_json):
    # {'id': 225404196, 'first_name': '音', 'is_bot': False, 'last_name': '抒情', 'username': 'Alyricing', 'language_code': 'zh-hans'}
    ret_name = ''
    if name_json['first_name']:
        ret_name += name_json['first_name']
    if name_json['last_name']:
        if ret_name:
            ret_name += ' '
        ret_name += name_json['last_name']

    if ret_name:
        return ret_name
    else:
        return 'who the fuck'


# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def echo(update: Update, context: CallbackContext) -> None:
    """Echo the user message."""
    update.message.reply_text(update.message.text)


def show(update: Update, context: CallbackContext) -> None:
    """Echo the user message."""
    try:
        print(parse_name(update.message.from_user), ':', update.message.text)
    except:
        return

    options = update.message.text.split()

class MeowBot:

    def __init__(self):
        X = np.genfromtxt('Meow_Quotes.csv', dtype=str, delimiter=',')
        self.data = {}
        for i, tag in enumerate(X[0]):
            self.data[tag] = []
            for j, s in enumerate(X[1:, i]):
                if s:
                    self.data[tag].append(s)
        self.tags = X[0, 1:]

        #with open('meow_tags.json', 'r') as f:
        #    self.tags = json.load(f)

    def meow(self, update: Update, context: CallbackContext) -> None:
        """Say something very MEOW"""
        ret = self.random_quote()
        update.message.reply_text(ret)

    def random_quote(self):
        ret = np.random.choice(self.data['quote'])
        for tag in self.tags:
            while tag in ret:
                ret = ret.replace('<'+tag+'>', np.random.choice(self.data[tag]), 1)
        return ret

def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    TOKEN = parse_token('meow_bot.token')
    if TOKEN:
        updater = Updater(TOKEN, use_context=True)
    else:
        print("token file not")

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    meow_bot = MeowBot()
    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("meow", meow_bot.meow))

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
    #meow_bot = MeowBot()
    #meow_bot.meow()
