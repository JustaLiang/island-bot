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
import copy

from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

from misc import parse_token, parse_name

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


def random_choice(x, size=None, replace=True, p=None):
    if p is not None:
       return np.random.choice(x, size, replace, p=(p / p.sum()))
    return np.random.choice(x, size, replace)

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
        self.probs = {}
        for tag in self.data:
            self.probs[tag] = np.ones(len(self.data[tag]), dtype=float)
            for i, it in enumerate(self.data[tag]):
                if tag == 'quote':
                    self.probs[tag][i] += it.count('<') #+ 3*it.count('adj')
                else:
                    pass
                    #if '撢' in it:
                    #    self.probs[tag][i] += 50
            self.probs[tag] = self.probs[tag] / self.probs[tag].sum()

    def meow(self, update: Update, context: CallbackContext) -> None:
        """Say something very MEOW"""
        options = update.message.text.split()
        source = parse_name(update.message.from_user)
        if len(options) == 1:
            ret = self._random_quote()
        elif len(options) > 2:
            ret = '{}，🤣🤣🤣'.format(source)
        else:
            keyword = options[1]
            probs = self._update_probs(keyword)
            if not probs:
                ret = '{}，{}🤣🤣🤣'.format(source, keyword)
            else:
                ret = self._random_quote(probs=probs)
        update.message.reply_text(ret, quote=False)

    def ref(self, update: Update, context: CallbackContext) -> None:
        """Return the reference of Meow Quotes"""
        options = update.message.text.split()
        source = parse_name(update.message.from_user)
        if len(options) == 1:
            update.message.reply_text('{}，你想找哪句的出處呀～'.format(source), quote=True)
        else:
            query = options[1:]
            ret = ''
            if len(query) == 1:
                try:
                    i = int(query[0])
                    if self.data['ref'][i]:
                        ret = '({}) '.format(i) + str(self.data['ref'][i])
                except:
                    pass

            for i, r in enumerate(self.data['ref']):
                has_q = True
                for q in query:
                    if q not in r:
                        has_q = False
                        break
                if not has_q:
                    continue
                if ret:
                    ret += '\n'
                ret += '({}) '.format(i) + r

            if not ret:
                ret = '{}，我找不到出處QQ'.format(source)
            ret = str(query) + ':\n' + ret

            return update.message.reply_text(ret, quote=False)

    def _init_probs(self):
        probs = {}
        for c in self.probs:
            probs[c] = np.zeros(len(self.data[c]), dtype=float) + 1e-6
        return probs

    def _update_probs(self, keyword):
        probs = self._init_probs()
        has_keyword = False
        for category in probs:
            if category == 'quote':
                continue
            for i, word in enumerate(self.data[category]):
                if keyword == word:
                    has_keyword = True
                    for j, t in enumerate(probs['quote']):
                        if category in self.data['quote'][j]:
                            probs['quote'][j] = 1
                    probs[category][i] = 1
                    break
            if has_keyword:
                break
        if not has_keyword:
            return False
        return probs



    def _replace_tags(self, line, probs=None):
        if probs is None:
            probs = self.probs
        for tag in self.tags:
            while '<'+tag+'>' in line:
                count = line.count('<{}>'.format(tag))
                choices = random_choice(self.data[tag], size=count, replace=False, p=probs[tag])
                for c in choices:
                    line = line.replace('<'+tag+'>', c, 1)
            line = line.replace('<name3_talent>', random_choice(self.data['name3'] + self.data['talent']), 1)
        return line

    def _random_quote(self, probs=None):
        if probs is None:
            probs = self.probs
        ret = random_choice(self.data['quote'], p=probs['quote'])
        return self._replace_tags(ret, probs)

    def hate(self, update: Update, context: CallbackContext) -> None:
        options = update.message.text.split()
        if len(options) != 2:
            source = parse_name(update.message.from_user)
            update.message.reply_text('{}，你想討論誰呀～'.format(source), quote=True)
        else:
            target = options[1]
            source = parse_name(update.message.from_user)

            mail = ''
            mail += self.data['quote'][0].replace('<name1>', source)
            print('Hating...')
            while True:
                coin = np.random.randint(0, 100)
                print(coin)
                if coin < 70:
                    sentence = random_choice(self.data['quote'][1:], p=self.probs['quote'][1:])
                    if '<name1>' in sentence:
                        sentence = sentence.replace('<name1>', target, 1)
                    elif '<name2>' in sentence:
                        sentence = sentence.replace('<name2>', target, 1)
                    elif '<name3>' in sentence:
                        sentence = sentence.replace('<name3>', target, 1)
                    sentence = self._replace_tags(sentence)
                    mail += ' ' + sentence
                elif coin < 95:
                    sentence = ' ' + random_choice(self.data['smooth'], p=self.probs['smooth'])
                else:
                    break

            update.message.reply_text(mail, quote=False)


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
    print('Meow Ready')
    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("hate", meow_bot.hate))
    dispatcher.add_handler(CommandHandler("meow", meow_bot.meow))
    dispatcher.add_handler(CommandHandler("ref", meow_bot.ref))

    # on noncommand i.e message - echo the message on Telegram
    # dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
    #dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, show))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
    #meow_bot = MeowBot()
