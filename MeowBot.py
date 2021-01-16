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

"""
tartarskunk: 1422967494

"""

import numpy as np
import json
import logging
import copy
import cv2
import imageio
import googletrans
import goslater

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

def random_choice(x, size=None, replace=True, p=None):
    if p is not None:
       return np.random.choice(x, size, replace, p=(p / p.sum()))
    return np.random.choice(x, size, replace)

class MeowBot:

    def __init__(self, bot):
        self.bot = bot
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

        self.translator = googletrans.Translator()
        #self.gr = goslater.Goslater()

    def _meow(self, options, source):
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
        return ret

    def meow(self, update: Update, context: CallbackContext) -> None:
        """Say something very MEOW"""
        options = update.message.text.split()
        source = parse_name(update.message.from_user)
        ret = self._meow(options, source)
        update.message.reply_text(ret, quote=False)

    def meow_jp(self, update: Update, context: CallbackContext) -> None:
        options = update.message.text.split()
        source = parse_name(update.message.from_user)
        ret_zhtw = self._meow(options, source)
        ret = self.translator.translate(ret_zhtw, dest='ja').text
        ret += '\n（中：{}）'.format(ret_zhtw)
        #x = self.gr.translate(ret_zhtw, 'ja')
        #print(x)
        #ret += '\n（Roman：{}）'.format(self.gr.translate(ret_zhtw, 'ja'))
        update.message.reply_text(ret, quote=False)

    def m_choose(self, update: Update, context: CallbackContext) -> None:
        options = update.message.text.split()
        source = parse_name(update.message.from_user)
        if len(options) == 1:
            update.message.reply_text('{}，你想選什麼呀～'.format(source), quote=True)
        else:
            hash_source = np.mod(np.sum([ord(c) for c in source]), 87)
            candidates = options[1:]
            hash_values = [ np.sum([ord(c) for c in s]) for s in candidates ]
            hash_values = [ np.mod(hash_source*h, 87) for h in hash_values ]
            best = candidates[np.argmax(hash_values)]

            ret = "{} 我好想你喔～ 我跟<adj>的<name3>不一樣 我跟你親近所以我才知道你的內心話呀 你想要 {} 對吧🤣".format(source, best)
            ret = self._replace_tags(ret)
            update.message.reply_text(ret, quote=True)

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

            update.message.reply_text(ret, quote=False)

    def jpg2png(self, update: Update, context: CallbackContext) -> None:
        '''
        source = parse_name(update.message.from_user)
        ret = "{} 你要不要試試看這個網址呀 \"https://jpg2png.com/\" 說不定你也可以成為jpg轉png方面的指導老師呦😃".format(source)
        update.message.reply_text(ret, quote=False)
        '''
        print('jpg2png')
        source = parse_name(update.message.from_user)
        file = update.message.document.get_file()
        assert(file.file_path.endswith('.jpg') or file.file_path.endswith('.jpeg'))
        file.download('test.jpg')

        x = imageio.imread('test.jpg')
        imageio.imwrite(x, 'test.png')
        update.message.reply_document('test.png', quote=False)

        print(source, file)

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

    def birthday(self, update: Update, context: CallbackContext) -> None:
        options = update.message.text.split()
        if len(options) != 2:
            source = parse_name(update.message.from_user)
            update.message.reply_text('{}，今天有人生日嗎？'.format(source), quote=True)
        else:
            target = options[1]
            ret = "{} 我好想你喔～ 我平常很<adj>所以沒想到今天是你的生日 生日快樂呦～🙂 下次有機會一定去<place>找你玩！".format(target)
            ret = self._replace_tags(ret)
            update.message.reply_text(ret, quote=False)

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


    def start_spy(self, update: Update, context: CallbackContext) -> None:
        options = update.message.text.split()
        user_json = update.message.from_user
        print(user_json)
        self.words = {}

    def register(self, update: Update, context: CallbackContext) -> None:
        options = update.message.text.split()
        user_id = update.message.from_user['id']
        usermame = update.message.from_user['username']
        if update.message.chat['type'] == 'private':
            chat_id = update.message.chat['id']
        update.message.chat.send_message('Hi')
        self.bot.send_message(chat_id, 'Hi')


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

    meow_bot = MeowBot(bot=updater.bot)
    print('Meow Ready')
    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("hate", meow_bot.hate))
    dispatcher.add_handler(CommandHandler("meow", meow_bot.meow))
    dispatcher.add_handler(CommandHandler("meow_jp", meow_bot.meow_jp))
    dispatcher.add_handler(CommandHandler("ref", meow_bot.ref))
    dispatcher.add_handler(CommandHandler("mchoose", meow_bot.m_choose))
    dispatcher.add_handler(CommandHandler("jpg2png", meow_bot.jpg2png))
    dispatcher.add_handler(CommandHandler("birthday", meow_bot.birthday))
    dispatcher.add_handler(CommandHandler("start_spy", meow_bot.start_spy))
    dispatcher.add_handler(CommandHandler("register", meow_bot.register))

    # on noncommand i.e message - echo the message on Telegram
    #dispatcher.add_handler(MessageHandler(Filters.photo, meow_bot.jpg2png))
    #dispatcher.add_handler(MessageHandler(Filters.all, meow_bot.jpg2png))
    #dispatcher.add_handler(MessageHandler(Filters.all, meow_bot.meow))
    #dispatcher.add_handler(MessageHandler(Filters.document.file_extension('txt'), meow_bot.meow))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
    #meow_bot = MeowBot()
