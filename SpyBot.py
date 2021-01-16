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

import telegram as tg
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, PollHandler, CallbackQueryHandler

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


def user_json2name(name_json):
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

def identity_str(i):
    if i == Identity.NEUTRAL:
        return '白板'
    elif i == Identity.CIVILIAN:
        return '平民'
    elif i == Identity.SPY:
        return '臥底'
    else:
        raise

class State(Enum):
    IDLE = 0
    INVITE = 1
    REGISTER = 2
    CLUE = 3
    POLL = 4
    KILL = 5
    DISCUSS = 6

class Player:
    def __init__(self, name, uid):
        self.name = name
        self.uid = uid
        self.clues = []
        self.identity = Identity.CIVILIAN
        self.alive = True
        self.votes = 0
        self.voted = False

class SpyBot:

    def __init__(self, bot):
        self.bot = bot

        self.num_identity_dict = {
            2: {Identity.NEUTRAL: 1, Identity.CIVILIAN: 1, Identity.SPY: 0},
            3: {Identity.NEUTRAL: 0, Identity.CIVILIAN: 2, Identity.SPY: 1},
            4: {Identity.NEUTRAL: 1, Identity.CIVILIAN: 2, Identity.SPY: 1},
            5: {Identity.NEUTRAL: 1, Identity.CIVILIAN: 3, Identity.SPY: 1},
            6: {Identity.NEUTRAL: 1, Identity.CIVILIAN: 4, Identity.SPY: 1},
            7: {Identity.NEUTRAL: 1, Identity.CIVILIAN: 4, Identity.SPY: 2},
        }

        self.words = {
            Identity.NEUTRAL: '(你是白板)',
            Identity.CIVILIAN: 'Orange',
            Identity.SPY: 'Apple'
        }
        self._reset()

    def _reset(self):
        self.current_state = State.IDLE
        self.history = []
        self.players = {}
        self.name2uid = {}
        self.identity_count = {}
        self.uid_wtp = {}

        self.current_poll_id = None
        self.current_register_id = None
        self.current_kill_id = None

    def reset(self, update: Update, context: CallbackContext) -> None:
        self._reset()

    def set(self, update: Update, context: CallbackContext) -> None:
        if self.current_state == State.REGISTER:
            cid = update.message.chat['id']
            uid = update.message.from_user['id']
            if cid > 0 and uid == self.host_uid and uid == cid:
                options = update.message.text.split()
                if len(options) == 3:
                    self.bot.send_message(uid,
                        f'將{options[1]}和{options[2]}隨機設定為平民或臥底詞彙')
                    words = options[1:]
                    np.random.shuffle(words)
                    self.words[Identity.CIVILIAN] = words[0]
                    self.words[Identity.SPY] = words[1]

    def spy(self, update: Update, context: CallbackContext) -> None:
        if self.current_state == State.IDLE:
            cid = update.message.chat['id']
            if cid > 0:
                self.bot.send_message(self.gid, '蛤？這裡沒人啊！')
            elif self.current_state != State.IDLE:
                self._reply_wrong_current_state(update)
            else:
                self.gid = update.message.chat['id']
                self.host_uid = update.message.from_user['id']
                self.host_name = user_json2name(update.message.from_user)

                keyboard = [[
                    tg.InlineKeyboardButton(callback_data=1, text='要'),
                    tg.InlineKeyboardButton(callback_data=-1, text='不要')]]
                reply_markup = tg.InlineKeyboardMarkup(keyboard)
                ret = self.bot.send_message(
                    self.gid, reply_markup=reply_markup, text=f"{self.host_name}想要玩，你要理他嗎？")
                self.current_register_id = ret.message_id
                self.current_state = State.REGISTER
                self.bot.send_message(
                    self.gid, f'主持人手動輸入題目 請先私訊SpyBot "/set 詞彙1 詞彙2"\n確定後再回來 "/game" \n不要再說我沒教了')

    def _register_button_handler(self, update):
        query = update.callback_query
        if query.message.message_id == self.current_register_id:
            if self.current_state == State.REGISTER:
                uid = query.from_user['id']
                name = user_json2name(query.from_user)
                if int(query.data) > 0:
                    if uid not in self.uid_wtp:
                        self.uid_wtp[uid] = True
                        self.players[uid] = Player(name, uid)
                        self.bot.send_message(self.gid,
                            f'{name} 想要玩')
                    elif self.uid_wtp[uid] == False:
                        self.players[uid] = Player(name, uid)
                        self.bot.send_message(self.gid,
                            f'{name} 想要玩')
                    else:
                        pass
                else:
                    if uid not in self.uid_wtp:
                        self.uid_wtp[uid] = False
                        self.bot.send_message(self.gid,
                            f'{name} 不想要理 {self.host_name}')
                    elif self.uid_wtp[uid] == True:
                        self.uid_wtp[uid] = False
                        del self.players[uid]
                        self.bot.send_message(self.gid,
                            f'{name} 不想要理 {self.host_name}')
                    elif self.uid_wtp[uid] == False:
                        pass
            else:
                self.bot.send_message(self.gid, f'等等啦 有人還在玩')

    def _kill_button_handler(self, update):
        query = update.callback_query
        if query.message.message_id == self.current_kill_id:
            if self.current_state == State.KILL:
                uid = query.from_user['id']
                name = user_json2name(query.from_user)
                if uid != self.host_uid:
                    self.bot.send_message(
                        self.gid, f'{name} 不要亂點 只有主持人{self.host_name}能按')
                elif int(query.data) in self.players:
                    self._kill(int(query.data))

    def button_handler(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        if query.message.message_id == self.current_poll_id:
            self._poll_button_handler(update)
        elif query.message.message_id == self.current_register_id:
            self._register_button_handler(update)
        elif query.message.message_id == self.current_kill_id:
            self._kill_button_handler(update)

    def _check_win(self):
        if self.identity_count[Identity.SPY] == 0:
            if self.identity_count[Identity.NEUTRAL] == 1:
                win_player = [ player.name for uid, player in self.players.items() if player.identity == Identity.NEUTRAL ]
                self.bot.send_message(
                    self.gid, f'{identity_str(Identity.NEUTRAL)}贏了: {win_player[0]}')
                self._show_words()
                return True
            elif self.identity_count[Identity.NEUTRAL] == 0:
                win_players = [ player.name for uid, player in self.players.items() if player.identity == Identity.CIVILIAN ]
                self.bot.send_message(
                    self.gid, f'{identity_str(Identity.CIVILIAN)}贏了: {", ".join(win_players)}')
                self._show_words()
                return True
        elif self.identity_count[Identity.NEUTRAL] == 0:
            if self.identity_count[Identity.SPY] > self.identity_count[Identity.CIVILIAN] or self.identity_count[Identity.CIVILIAN] == 1:
                win_players = [ player.name for uid, player in self.players.items() if player.identity == Identity.SPY ]
                self.bot.send_message(
                    self.gid, f'{identity_str(Identity.SPY)}贏了: {", ".join(win_players)}')
                self._show_words()
                return True
        return False

    def _show_words(self):
        ret = f'{identity_str(Identity.CIVILIAN)}: {self.words[Identity.CIVILIAN]}\n'
        ret += f'{identity_str(Identity.SPY)}: {self.words[Identity.SPY]}'
        self.bot.send_message(self.gid, ret)

    def _reply_wrong_current_state(self, update):
        update.message.reply_text(f"時候未到，現在{self.current_state}中", quote=True)

    def _reply_not_host(self, update=None):
        name = user_json2name(update.message.from_user)
        if update is None:
            self.bot.send_message(self.gid,
                f'{name} 不要亂點 只有主持人{self.host_name}能按')
        else:
            update.message.reply_text(
                f'{name} 不要亂點 只有主持人{self.host_name}能按', quote=True)

    def _show_identity_count(self):
        ret = []
        for x in self.identity_count:
            ret.append(f' {self.identity_count[x]}位{identity_str(x)}')
        self.bot.send_message(self.gid, ' '.join(ret))

    def game(self, update: Update, context: CallbackContext) -> None:
        num_players = len(self.players)
        uid = update.message.from_user['id']
        if self.current_state != State.REGISTER:
            self._reply_wrong_current_state(update)
        elif uid != self.host_uid:
            self._reply_not_host(update)
        elif num_players == 0:
            self.bot.send_message(self.gid, f'目前沒有人想理{self.host_name}')
        elif num_players == 1:
            self.bot.send_message(self.gid, f'{self.host_name}白癡喔 一個人怎麼玩')

        else:
            players_info = []
            identity_list = []
            N = len(self.players)
            if N not in self.num_identity_dict:
                self.bot.send_message(self.gid, f'人數過多或過少')
            else:
                self.identity_count = copy.deepcopy(self.num_identity_dict[N])

                self.bot.send_message(self.gid, f'本局玩家{N}人')
                for x in [Identity.NEUTRAL, Identity.CIVILIAN, Identity.SPY]:
                    for _ in range(self.identity_count[x]):
                        identity_list.append(x)
                self._show_identity_count()

                np.random.shuffle(identity_list)
                for i, (uid, player) in enumerate(self.players.items()):
                    self.name2uid[player.name] = uid
                    player.identity = identity_list[i]
                    players_info.append('\t'+player.name)
                    self.bot.send_message(uid, f'{player.name} 你的字是：\n{self.words[player.identity]}')
                players_info_str = '\n'.join(players_info)
                self.bot.send_message(self.gid, '玩家有:\n{}'.format(players_info_str))
                self._init_turn()

    def clue(self, update: Update, context: CallbackContext) -> None:
        options = update.message.text.split()
        uid = update.message.from_user['id']
        name = user_json2name(update.message.from_user)
        if self.current_state != State.CLUE:
            self._reply_wrong_current_state(update)
        elif uid not in self.players:
            update.message.reply_text(
                f'{name} 閉嘴 你剛又沒有說要玩', quote=True)
        elif uid != self.next_uid:
            update.message.reply_text(
                f'{name} 閉嘴 你不是 {self.players[self.next_uid].name}', quote=True)
        elif update.message.chat['id'] >= 0:
            # No Private
            update.message.reply_text(
                f'{name} 有種大聲說出來', quote=True)
        elif len(options) < 2:
            update.message.reply_text(
                f'{name} 你當我會通靈嗎', quote=True)
        else:
            clue = ' '.join(options[1:])
            self.players[uid].clues.append(clue)
            self.history.append( (name, clue) )
            self._next_player()

    def _init_turn(self):
        self.players_order = [ uid for uid, player in self.players.items() if player.alive ]
        np.random.shuffle(self.players_order)
        players_order_name = [ self.players[uid].name for uid in self.players_order ]
        self.bot.send_message(self.gid, f'本局順序為 {",".join(players_order_name)}')
        self.index = -1
        self.current_state = State.CLUE
        self._next_player()

    def _next_player(self):
        self.index += 1
        num_alive = len([ player for uid, player in self.players.items() if player.alive ])
        if self.index == num_alive:
            self._start_discuss()
        else:
            self.next_uid = self.players_order[self.index]
            self.bot.send_message(self.gid, f'{self.players[self.next_uid].name} 輪到你了 講話啊')

    def _start_discuss(self):
        self.bot.send_message(self.gid, '大家都說完了吧')
        self._show_history()
        self.bot.send_message(self.gid, '請開始你們的內鬨')
        self.current_state = State.DISCUSS

    def _show_history(self):
        ret = '剛剛都說了這些：'
        #for h in self.players:
        #    ret += f'\n{h[0]} 提示 {h[1]}'
        for uid, player in self.players.items():
            ret += f'\n{player.name}: {" ".join(player.clues)}'
        self.bot.send_message(self.gid, ret)

    def poll(self, update: Update, context: CallbackContext) -> None:
        uid = update.message.from_user['id']
        name = user_json2name(update.message.from_user)
        if self.current_state != State.DISCUSS:
            self._reply_wrong_current_state(update)
        elif uid != self.host_uid:
            self._reply_not_host(update)
        else:
            self._send_poll()

    def _send_poll(self, value=-1):
        keyboard = [[]]
        self.expected_votes = 0
        for uid, player in self.players.items():
            player.voted = False
            if player.alive:
                self.expected_votes += 1
                if player.votes >= value:
                    keyboard[0].append(tg.InlineKeyboardButton(callback_data=player.uid, text=player.name))
        reply_markup = tg.InlineKeyboardMarkup(keyboard)
        ret = self.bot.send_message(
            self.gid, reply_markup=reply_markup, text=f"你們要殺誰？")

        for uid in self.players:
            self.players[uid].votes = 0
        self.current_poll_id = ret.message_id
        self.current_state = State.POLL

    def kill(self, update: Update, context: CallbackContext) -> None:
        uid = update.message.from_user['id']
        name = user_json2name(update.message.from_user)
        if self.current_state == State.CLUE:
            keyboard = [[]]
            for uid, player in self.players.items():
                if player.alive:
                    keyboard[0].append(tg.InlineKeyboardButton(callback_data=player.uid, text=player.name))
            reply_markup = tg.InlineKeyboardMarkup(keyboard)
            ret = self.bot.send_message(
                self.gid, reply_markup=reply_markup, text=f"主持人強制執行")
            self.current_kill_id = ret.message_id
            self.current_state = State.KILL

    def _kill(self, victim_uid):
        victim_name = self.players[victim_uid].name

        self.players[victim_uid].alive = False
        victim_identity = self.players[victim_uid].identity
        self.bot.send_message(
            self.gid, f'{victim_name} 死了 他的身份是{identity_str(victim_identity)}')
        self.identity_count[victim_identity] -= 1
        self._show_identity_count()
        if self._check_win():
            self._reset()
            return
        self._init_turn()

        '''
        keyboard = [[
            tg.InlineKeyboardButton(callback_data=2, text=f'{self.victim_name}死好'),
            tg.InlineKeyboardButton(callback_data=-2, text='再等等')]]
        reply_markup = tg.InlineKeyboardMarkup(keyboard)
        ret = self.bot.send_message(
            self.gid, reply_markup=reply_markup, text=f"確定要殺 {self.victim_name} 嗎？")
        self.current_kill_id = ret.message_id
        self.current_state = State.KILL
        '''

    def test(self, update: Update, context: CallbackContext) -> None:
        print(update.message)

    def _poll_button_handler(self, update):
        query = update.callback_query
        if query.message.message_id == self.current_poll_id:
            if self.current_state == State.POLL:
                uid = query.from_user['id']
                name = user_json2name(query.from_user)
                if (uid not in self.players) or (not self.players[uid].alive) or (self.players[uid].voted):
                    pass
                else:
                    tgt_uid = int(query.data)
                    self.players[uid].voted = tgt_uid
                    self.players[tgt_uid].votes += 1
                    for uid, player in self.players.items():
                        print(player.name, player.votes)

                    self.expected_votes -= 1
                    self.bot.send_message(
                        self.gid, f'{name} 投票了')

                    if self.expected_votes == 0:
                        for uid, player in self.players.items():
                            ret = []
                            if self.players[uid].alive:
                                ret.append(f'{player.name} 投給了 {self.players[player.voted].name}')
                            ret = '\n'.join(ret)
                            self.bot.send_message(self.gid, ret)

                        votes = [[uid, player.votes] for uid, player in self.players.items() ]
                        sorted_votes = sorted(votes, key=lambda x: -x[1])
                        if sorted_votes[0][1] == sorted_votes[1][1]:
                            self.bot.send_message(
                                self.gid, text=f"出現平手 請重新投票")
                            self._send_poll(value=sorted_votes[0][1])
                            return

                        self._kill(sorted_votes[0][0])

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
    dispatcher.add_handler(CommandHandler("start", spy_bot.reset))
    dispatcher.add_handler(CommandHandler("spy", spy_bot.spy))
    dispatcher.add_handler(CommandHandler("set", spy_bot.set))
    dispatcher.add_handler(CommandHandler("game", spy_bot.game))
    dispatcher.add_handler(CommandHandler("clue", spy_bot.clue))
    dispatcher.add_handler(CommandHandler("test", spy_bot.test))
    dispatcher.add_handler(CommandHandler("kill", spy_bot.kill))
    dispatcher.add_handler(CommandHandler("poll", spy_bot.poll))
    dispatcher.add_handler(CommandHandler("reset", spy_bot.reset))
    #dispatcher.add_handler(CommandHandler("history", spy_bot.history))

    dispatcher.add_handler(CallbackQueryHandler(spy_bot.button_handler))

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
