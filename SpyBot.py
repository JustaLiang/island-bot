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
import imageio

from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

"""
{'id': 225404196, 'type': 'private', 'username': 'Alyricing', 'first_name': '音', 'last_name': '抒情'}
{'id': 1483514012, 'type': 'private', 'username': 'gym7012', 'first_name': '鑫'}
1483514012 1483514012 鑫
{'id': 1496518066, 'type': 'private', 'username': 'justajunk', 'first_name': 'Island', 'last_name': 'Man'}
1496518066 1496518066 Island Man
225404196 225404196 音 抒情
{'id': 1032245229, 'type': 'private', 'username': 'DanchifromTW', 'first_name': 'PPer in TW'}


"""


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

from enum import Enum

class Identity(Enum):
    NEUTRAL = 0
    CIVILIAN = 1
    SPY = -1

class Player:
    def __init__(self, name, uid, cid):
        self.name = name
        self.uid = uid
        self.cid = cid
        self.clues = []

class SpyBot:

    def __init__(self, bot):
        self.bot = bot
        self.state = 'halt'

        self.host_id = 1422967494

        self.num_dict = {
            3: {Identity.NEUTRAL: 0, Identity.CIVILIAN: 2, Identity.SPY: 1},
            4: {Identity.NEUTRAL: 0, Identity.CIVILIAN: 3, Identity.SPY: 1},
            5: {Identity.NEUTRAL: 1, Identity.CIVILIAN: 3, Identity.SPY: 1},
            6: {Identity.NEUTRAL: 1, Identity.CIVILIAN: 4, Identity.SPY: 1},
            7: {Identity.NEUTRAL: 1, Identity.CIVILIAN: 4, Identity.SPY: 2},
        }

        self.word_dict = {
            Identity.NEUTRAL: '(你是白板)',
            Identity.CIVILIAN: 'Orange',
            Identity.SPY: 'Apple'
        }
        self.index = -1
        self.state = 'sleep'

    def start(self, update: Update, context: CallbackContext) -> None:
        options = update.message.text.split()
        user_id = update.message.from_user['id']
        print(update.message.chat)
        if self.state == 'sleep':
            if update.message.chat['id'] < 0:
                self.gid = update.message.chat['id']
                if user_id == self.host_id:
                    self.bot.send_message(self.gid, '開放註冊')
                    self.bot.send_message(self.gid, '請想要玩的人私訊我\"/register\"')
                    self.players = {}
                    self.state = 'register'

    def game(self, update: Update, context: CallbackContext) -> None:
        num_players = len(self.players)

        if num_players > 0 and self.state == 'register':
            players_info = []
            for uid in self.players:
                players_info.append('\t'+self.players[uid].name)
                player = self.players[uid]
                self.bot.send_message(player.cid, '你的字是：\n{}'.format(
                    self.word_dict[player.identity]))
            players_info_str = '\n'.join(players_info)
            self.bot.send_message(self.gid, '玩家有:\n{}'.format(players_info_str))
            self._init_turn()
        else:
            pass

    def _next_player(self):
        self.index += 1
        if self.index == len(self.players):
            history = []
            for uid in self.players:
                player = self.players[uid]
                history.append('{}: {}'.format(player.name, player.clues[-1]))
            history_str = '\n'.join(history)
            self.bot.send_message(self.gid, '大家都說完提示了')
            self.bot.send_message(self.gid, history_str)
            self.bot.send_message(self.gid, '請開始投票')
            self.state = 'polling'
            self._init_turn()
        else:
            self.next_uid = self.players_order[self.index]
            self.state = 'clue'
            self.bot.send_message(self.gid, '{} 請說提示'.format(
                self.players[self.next_uid].name))

    def spy_clue(self, update: Update, context: CallbackContext) -> None:
        options = update.message.text.split()
        print(update.message)

        uid = update.message.from_user['id']
        if self.state != 'clue':
            update.message.reply_text('時候未到', quote=True)
        elif uid != self.next_uid:
            update.message.reply_text('騙人，你不是 {}'.format(
                    self.players[self.next_uid].name), quote=True)
        elif update.message.chat['id'] >= 0:
            # No Private
            update.message.reply_text('{} 請大聲在群組說出來'.format(
                self.players[self.next_uid].name), quote=True)
        elif len(options) != 2:
            update.message.reply_text('指令錯誤', quote=True)
        else:
            clue = options[1]
            self.players[self.next_uid].clues.append(clue)
            self._next_player()

    def _init_turn(self):
        self.players_order = [ uid for uid in self.players ]
        np.random.shuffle(self.players_order)
        print(self.players_order)
        self.index = -1
        self._next_player()

    def register(self, update: Update, context: CallbackContext) -> None:
        options = update.message.text.split()
        uid = update.message.from_user['id']
        name = parse_name(update.message.from_user)
        if self.state == 'register':
            if update.message.chat['type'] == 'private':
                cid = update.message.chat['id']
                if uid not in self.players:
                    player = Player(name, uid, cid)
                    self.bot.send_message(cid, '註冊 {} '.format(name))
                    self.bot.send_message(self.gid, '{} 想要玩'.format(name))
                    player.identity = np.random.choice([Identity.NEUTRAL, Identity.CIVILIAN, Identity.SPY])
                    self.players[uid] = player
                    print(uid, cid, name)
                else:
                    self.bot.send_message(cid, '{} 已註冊過了'.format(name))
        else:
            update.message.reply_text('目前不開放註冊新玩家', quote=True)

    def poll(self, update: Update, context: CallbackContext) -> None:
        pass

    def test(self, update: Update, context: CallbackContext) -> None:
        print(update.message)

def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    token = open('XTalkSpyBot.token', 'r').read()
    updater = Updater(token, use_context=True)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    spy_bot = SpyBot(bot=updater.bot)
    dispatcher.add_handler(CommandHandler("start", spy_bot.start))
    dispatcher.add_handler(CommandHandler("register", spy_bot.register))
    dispatcher.add_handler(CommandHandler("game", spy_bot.game))
    dispatcher.add_handler(CommandHandler("clue", spy_bot.spy_clue))
    dispatcher.add_handler(CommandHandler("test", spy_bot.test))


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
