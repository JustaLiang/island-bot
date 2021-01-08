#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

from misc import parse_token, parse_name
import numpy as np
import json

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

# Global variables
self_name = 'Island Bot'
token_file = 'token_CD_info_bot'
user_json = {}

# Functions
def save_user_id(from_user):
    if from_user.full_name not in user_json:
        user_json[from_user.full_name] = from_user.id

def show(update: Update, context: CallbackContext) -> None:
	if update.message is None:
        return

    save_user_id(update.message.from_user)
    print(parse_name(update.message.from_user), ':', update.message.text)


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

    # on noncommand i.e message - echo the message on Telegram
    # dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
    dispatcher.add_handler(MessageHandler(Filters.all, show))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

    # print(user_json)
    # with open('user.json', 'w', encoding='utf8') as outfile:
    #     json.dump(user_json, outfile, indent=4, ensure_ascii=False)

    print(user_json)
    with open('user.json', 'w', encoding='utf8') as outfile:
        json.dump(user_json, outfile, indent=4, ensure_ascii=False)
    
if __name__ == '__main__':
    main()