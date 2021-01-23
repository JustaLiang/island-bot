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
import util

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
from SpyGame import SpyGame
from SpyGame import State

class SpyBot:

    def __init__(self, bot):
        self.bot = bot
        self.tutorial_str = open("SpyHostTutorial.txt", 'r').read()
        self.games = {}

        self.game_index = 0
        self.c_id_list = []

    def tutorial(self, update: Update, context: CallbackContext) -> None:
        c_id, u_id, u_name, m_id = util.message_info(update.message)
        self.bot.send_message(u_id, self.tutorial_str)

    def spy(self, update: Update, context: CallbackContext) -> None:
        c_id, u_id, u_name, m_id = util.message_info(update.message)
        if c_id < 0:
            if c_id in self.games:
                game = self.games[c_id]
                if game.state == State.IDLE:
                    self.bot.send_message(c_id, f'遊戲已繼續 新主持人為{u_name}')
                    game.h_id = u_id
                    game.h_name = u_name
                else:
                    self.bot.send_message(c_id, f'前局遊戲尚未結束')
                    return
            else:
                self.game_index += 1
                self.c_id_list.append(c_id)
                game = SpyGame(c_id=c_id, h_id=u_id, h_name=u_name)
                game.g_id = self.game_index
                self.games[c_id] = game
                info_str = f'{game.g_id}號房已建立 目前主持人為{u_name}'
                info_str += f'\n主持人欲設定詞彙請私訊SpyBot "/set_words <房號> <詞彙1> <詞彙2>"'
                info_str += '\n若需教學請輸入"/tutorial"'

                self.bot.send_message(c_id, info_str)

            keyboard = [[
                tg.InlineKeyboardButton(callback_data=1, text='要'),
                tg.InlineKeyboardButton(callback_data=-1, text='不要')
            ]]
            ret_msg = self.bot.send_message(c_id,
                reply_markup=tg.InlineKeyboardMarkup(keyboard),
                text=f"{game.h_name}想要玩，你要理他嗎？")
            game.m_id['register_button'] = ret_msg.message_id
            ret_msg = self.bot.send_message(c_id,
                text=util.players_want2play_str(game.players))
            game.m_id['register_players'] = ret_msg.message_id
            game.state = State.REGISTER
        else:
            # 私訊
            self.bot.send_message(c_id, '蛤？這裡沒人啊！')

    def game(self, update: Update, context: CallbackContext) -> None:
        c_id, u_id, u_name, m_id = util.message_info(update.message)
        if c_id > 0:
            # 私訊
            pass
            return
        elif c_id not in self.games:
            # 請先/spy
            pass
            return
        game = self.games[c_id]
        N = len([ player for u_id, player in game.players.items() if player.play ])
        if game.state != State.REGISTER:
            self.bot.send_message(
                c_id, game.wrong_state(),
                reply_to_message_id=m_id)
        elif u_id != game.h_id:
            self.bot.send_message(
                c_id, game.not_host(),
                reply_to_message_id=m_id)
        elif N == 0:
            self.bot.send_message(
                c_id, f'目前沒有人想理{game.h_name}')
        #elif N == 1:
        #    self.bot.send_message(c_id, f'{game.h_name}白癡喔 一個人怎麼玩')
        #elif N not in game.num_identity_dict:
        #    self.bot.send_message(c_id, f'人數過多或過少 目前只支援2-7人')
        else:
            self.bot.delete_message(c_id, game.m_id['register_button'])
            game.m_id['register_button'] = -1

            game.random_set_player_identity()
            info_str = f'本局玩家{N}人'
            info_str += '\n' + game.log_players_name()
            info_str += '\n' + game.log_identity_count()
            self.bot.send_message(
                c_id, info_str)

            for i, (u_id, player) in enumerate(game.players.items()):
                if player.play:
                    self.bot.send_message(
                        u_id, f'{player.name} 你在{game.g_id}號房的詞是：\n{game.words[player.identity]}')
            self.next_turn(c_id)

    def clue(self, update: Update, context: CallbackContext) -> None:
        options = update.message.text.split()
        c_id, u_id, u_name, m_id = util.message_info(update.message)
        if c_id not in self.games:
            return
        game = self.games[c_id]
        if game.state != State.CLUE:
            self.bot.send_message(
                c_id, game.wrong_state(),
                reply_to_message_id=m_id)
        elif u_id not in game.players:
            update.message.reply_text(
                f'{u_name} 閉嘴 你剛又沒有說要玩', quote=True)
        elif u_id != game.next_u_id:
            update.message.reply_text(
                f'{u_name} 閉嘴 你不是 {game.next_u_name}', quote=True)
        elif len(options) < 2:
            update.message.reply_text(
                f'{u_name} 你當我會通靈嗎', quote=True)
        else:
            clue = ' '.join(options[1:])
            game.add_clue(u_id, clue)
            ret, info_str = game.next_player()
            self.bot.send_message(
                c_id, info_str)

    def skip(self, update: Update, context: CallbackContext) -> None:
        c_id, u_id, u_name, m_id = util.message_info(update.message)
        if c_id not in self.games:
            pass
            return
        game = self.games[c_id]
        if u_id != game.h_id:
            self.bot.send_message(
                c_id, game.not_host(), reply_to_message_id=m_id)
        elif game.state != State.CLUE:
            self.bot.send_message(
                c_id, game.wrong_state(), reply_to_message_id=m_id)
        else:
            ret, info_str = game.next_player()
            self.bot.send_message(
                c_id, info_str)

    def skip_all(self, update: Update, context: CallbackContext) -> None:
        c_id, u_id, u_name, m_id = util.message_info(update.message)
        if c_id not in self.games:
            pass
            return
        game = self.games[c_id]
        if u_id != game.h_id:
            self.bot.send_message(
                c_id, game.not_host(), reply_to_message_id=m_id)
        elif game.state != State.CLUE:
            self.bot.send_message(
                c_id, game.wrong_state(), reply_to_message_id=m_id)
        else:
            ret, info_str = game.end_turn()
            self.bot.send_message(
                c_id, info_str)

    def poll(self, update: Update, context: CallbackContext) -> None:
        c_id, u_id, u_name, m_id = util.message_info(update.message)
        if c_id not in self.games:
            pass
            return
        game = self.games[c_id]
        if u_id != game.h_id:
            self.bot.send_message(
                c_id, game.not_host(), reply_to_message_id=m_id)
        elif game.state != State.DISCUSS:
            self.bot.send_message(
                c_id, game.wrong_state(), reply_to_message_id=m_id)
        else:
            self.send_poll(c_id)

    def send_poll(self, c_id, value=-1):
        game = self.games[c_id]
        game.poll_keyboard = [[]]
        game.expected_votes = 0
        for u_id, player in game.players.items():
            if player.alive and player.play:
                game.expected_votes += 1
                if player.votes >= value:
                    game.poll_keyboard[0].append(tg.InlineKeyboardButton(callback_data=player.id, text=player.name))
            player.voted = False
            player.votes = 0
        game.poll_reply_markup = tg.InlineKeyboardMarkup(game.poll_keyboard)

        voted_str = game.log_voted()
        ret_msg = self.bot.send_message(
            c_id,
            text=f'你們要殺誰？ 目前還剩有{game.log_identity_count()}\n{voted_str}',
            reply_markup=game.poll_reply_markup
        )

        game.m_id['poll_button'] = ret_msg.message_id
        game.set_state(State.POLL)

    def button_handler_registor(self, update):
        query = update.callback_query
        #query.answer(text="處理中...", show_alert=True)
        c_id, _, _, _ = util.message_info(query.message)
        u_id = query.from_user.id
        u_name = query.from_user.full_name
        if c_id in self.games:
            game = self.games[c_id]
            if game.state == State.REGISTER:
                update = game.register(u_id, u_name, play=int(query.data)>0)
                if update:
                    self.bot.edit_message_text(
                        util.players_want2play_str(game.players),
                        c_id, game.m_id['register_players']
                    )
            else:
                self.bot.send_message(c_id, f'等等啦 有人還在玩')

    def button_handler_poll(self, update):
        query = update.callback_query
        #query.answer(text="處理中...", show_alert=True)
        c_id, _, _, _ = util.message_info(query.message)
        u_id = query.from_user.id
        u_name = query.from_user.full_name
        if c_id in self.games:
            game = self.games[c_id]
            if game.state == State.POLL:
                if u_id not in game.players:
                    pass
                else:
                    player = game.players[u_id]
                    if player.alive and player.play and player.voted == False:
                        tgt_u_id = int(query.data)
                        player.voted = tgt_u_id
                        game.players[tgt_u_id].votes += 1

                        #for u_id, player in game.players.items():
                        #    print(player.name, player.votes)

                        game.expected_votes -= 1
                        voted_str = game.log_voted()

                        self.bot.edit_message_text(
                            f'你們要殺誰？ 目前還剩有{game.log_identity_count()}\n{voted_str}',
                            c_id, game.m_id['poll_button'],
                            reply_markup=game.poll_reply_markup
                        )


                        if game.expected_votes == 0:
                            self.conclude_poll(c_id)

    def button_handler_kill(self, update):
        query = update.callback_query
        c_id, _, _, _ = util.message_info(query.message)
        u_id = query.from_user.id
        u_name = query.from_user.full_name
        if c_id in self.games:
            game = self.games[c_id]
            if game.state == State.KILL:
                if u_id != game.h_id:
                    self.bot.send_message(
                        c_id, game.not_host())
                elif int(query.data) in game.players:
                    victim_u_id = int(query.data)
                    query.answer()

                    win, info_str = game.kill_player(victim_u_id)
                    self.bot.send_message(
                        c_id, text=info_str)
                    self.bot.delete_message(c_id, game.m_id['kill_button'])

                    if win[0]:
                        self.bot.send_message(
                            c_id, text=win[1])
                        game.reset()
                    else:
                        self.bot.send_message(
                            c_id, text=win[1])
                        self.next_turn(c_id)

    def button_handler_host(self, update):
        query = update.callback_query
        c_id, _, _, _ = util.message_info(query.message)
        u_id = query.from_user.id
        u_name = query.from_user.full_name
        if c_id in self.games:
            game = self.games[c_id]
            if u_id != game.h_id:
                self.bot.send_message(
                    c_id, game.not_host())
            elif int(query.data) in game.players:
                next_host_u_id = int(query.data)
                query.answer()
                self.bot.delete_message(c_id, game.m_id['host_button'])

                if next_host_u_id == game.h_id:
                    self.bot.send_message(
                        c_id,f'{game.h_name}你在靠夭喔 根本沒換啊')
                else:
                    game.h_id = next_host_u_id
                    next_host_u_name = game.players[next_host_u_id].name
                    game.h_name = next_host_u_name

                    self.bot.send_message(
                        c_id,f'大家注意 主持人換成{game.h_name}囉')

    def end_poll(self, update: Update, context: CallbackContext) -> None:
        c_id, u_id, u_name, m_id = util.message_info(update.message)
        if c_id not in self.games:
            pass
            return
        game = self.games[c_id]
        if u_id != game.h_id:
            self.bot.send_message(
                c_id, game.not_host(), reply_to_message_id=m_id)
        elif game.state != State.POLL:
            self.bot.send_message(
                c_id, game.wrong_state(), reply_to_message_id=m_id)
        else:
            self.conclude_poll(c_id)

    def conclude_poll(self, c_id):
        game = self.games[c_id]
        voted_str = []
        for u_id, player in game.players.items():
            if player.alive and player.play and (player.voted != False):
                voted_str.append(f'{player.name} 投給了 {game.players[player.voted].name}')
        voted_str = '\n'.join(voted_str)

        self.bot.send_message(
                c_id, text=voted_str)
        self.bot.delete_message(c_id, game.m_id['poll_button'])
        game.m_id['poll_button'] = -1

        votes = [[u_id, player.votes] for u_id, player in game.players.items() ]
        sorted_votes = sorted(votes, key=lambda x: -x[1])
        if len(sorted_votes) > 1 and (sorted_votes[0][1] == sorted_votes[1][1]):
            self.bot.send_message(
                c_id, text=f"出現平手 請重新投票")
            self.send_poll(c_id, value=sorted_votes[0][1])
            return

        win, info_str = game.kill_player(sorted_votes[0][0])
        self.bot.send_message(
            c_id, text=info_str)

        if win[0]:
            self.bot.send_message(
                c_id, text=win[1])
            game.reset()
        else:
            self.bot.send_message(
                c_id, text=win[1])
            self.next_turn(c_id)

    def next_turn(self, c_id):
        game = self.games[c_id]
        info_str = game.init_turn()
        self.bot.send_message(
            c_id, info_str)

        _, info_str = game.next_player()
        self.bot.send_message(
            c_id, info_str)

    def kill(self, update: Update, context: CallbackContext) -> None:
        c_id, u_id, u_name, m_id = util.message_info(update.message)
        if c_id not in self.games:
            pass
            return
        game = self.games[c_id]
        if u_id != game.h_id:
            self.bot.send_message(
                c_id, game.not_host(), reply_to_message_id=m_id)
            return
        if game.state == State.CLUE or game.state == State.DISCUSS:
            keyboard = [[]]
            for u_id, player in game.players.items():
                if player.alive and player.play:
                    keyboard[0].append(tg.InlineKeyboardButton(callback_data=u_id, text=player.name))
            reply_markup = tg.InlineKeyboardMarkup(keyboard)
            ret_msg = self.bot.send_message(
                c_id, reply_markup=reply_markup, text=f"主持人{game.h_name}要強制殺人囉～")
            game.m_id['kill_button'] = ret_msg.message_id
            game.set_state(State.KILL)

    def set_host(self, update: Update, context: CallbackContext) -> None:
        c_id, u_id, u_name, m_id = util.message_info(update.message)
        if c_id not in self.games:
            pass
            return
        game = self.games[c_id]
        if u_id != game.h_id:
            self.bot.send_message(
                c_id, game.not_host(), reply_to_message_id=m_id)
        else:
            keyboard = [[]]
            #keyboard[0].append(tg.InlineKeyboardButton(callback_data=game.h_id, text=player.name))
            for u_id, player in game.players.items():
                keyboard[0].append(tg.InlineKeyboardButton(callback_data=u_id, text=player.name))
            reply_markup = tg.InlineKeyboardMarkup(keyboard)
            ret_msg = self.bot.send_message(
                c_id, reply_markup=reply_markup, text=f"主持人{game.h_name}不想幹了 要交棒～")
            game.m_id['host_button'] = ret_msg.message_id

    def button_handler(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        c_id, u_id, u_name, m_id = util.message_info(query.message)
        if c_id in self.games:
            game = self.games[c_id]
            #print(game.wait_register_button_m_id)
            if query.message.message_id == game.m_id['register_button']:
                self.button_handler_registor(update)
            elif query.message.message_id == game.m_id['poll_button']:
                self.button_handler_poll(update)
            elif query.message.message_id == game.m_id['kill_button']:
                self.button_handler_kill(update)
            elif query.message.message_id == game.m_id['host_button']:
                self.button_handler_host(update)

    def set_words(self, update: Update, context: CallbackContext) -> None:
        private_id, u_id, u_name, m_id = util.message_info(update.message)
        options = update.message.text.split()
        if private_id > 0:
            if len(options) == 4:
                g_id = int(options[1])
                try:
                    c_id = self.c_id_list[g_id-1]
                except:
                    raise
                if c_id in self.games:
                    game = self.games[c_id]
                    if game.state == State.IDLE or game.state == State.REGISTER:
                        if u_id == game.h_id:
                            ret_msg = game.set_words(options[2], options[3], random=True)
                            self.bot.send_message(u_id, ret_msg)

    def remain(self, update: Update, context: CallbackContext) -> None:
        c_id, u_id, u_name, m_id = util.message_info(update.message)
        if c_id not in self.games:
            pass
            return
        game = self.games[c_id]
        self.bot.send_message(c_id, f'目前還剩有 {game.log_identity_count()}')

    def history(self, update: Update, context: CallbackContext) -> None:
        c_id, u_id, u_name, m_id = util.message_info(update.message)
        if c_id not in self.games:
            pass
            return
        game = self.games[c_id]
        self.bot.send_message(c_id, f'{game.log_clue_history()} \n目前還剩有 {game.log_identity_count()}')

    def init(self, update: Update, context: CallbackContext) -> None:
        c_id, u_id, u_name, m_id = util.message_info(update.message)
        if c_id not in self.games:
            pass
            return
        game = self.games[c_id]
        if u_id != game.h_id:
            self.bot.send_message(
                c_id, game.not_host(), reply_to_message_id=m_id)
        else:
            game.init()

    def reset(self, update: Update, context: CallbackContext) -> None:
        c_id, u_id, u_name, m_id = util.message_info(update.message)
        if c_id not in self.games:
            pass
            return
        game = self.games[c_id]
        if u_id != game.h_id:
            self.bot.send_message(
                c_id, game.not_host(), reply_to_message_id=m_id)
        else:
            game.reset()

    def set_state(self, update: Update, context: CallbackContext) -> None:
        c_id, u_id, u_name, m_id = util.message_info(update.message)
        options = update.message.text.split()
        if c_id not in self.games:
            pass
            return
        game = self.games[c_id]
        state_value = int(options[1])
        game.set_state(State(state_value))
        self.bot.send_message(
            c_id, f'已將game state設定為{str(game.state)}')

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
    #dispatcher.add_handler(CommandHandler("start", spy_bot.reset))
    dispatcher.add_handler(CommandHandler("spy", spy_bot.spy))
    dispatcher.add_handler(CommandHandler("set_words", spy_bot.set_words))
    dispatcher.add_handler(CommandHandler("game", spy_bot.game))
    dispatcher.add_handler(CommandHandler("clue", spy_bot.clue))
    dispatcher.add_handler(CommandHandler("skip", spy_bot.skip))
    dispatcher.add_handler(CommandHandler("skip_all", spy_bot.skip_all))
    dispatcher.add_handler(CommandHandler("set_host", spy_bot.set_host))
    dispatcher.add_handler(CommandHandler("set_state", spy_bot.set_state))
    dispatcher.add_handler(CommandHandler("kill", spy_bot.kill))
    dispatcher.add_handler(CommandHandler("poll", spy_bot.poll))
    dispatcher.add_handler(CommandHandler("remain", spy_bot.remain))
    dispatcher.add_handler(CommandHandler("end_poll", spy_bot.end_poll))
    dispatcher.add_handler(CommandHandler("init", spy_bot.init))
    dispatcher.add_handler(CommandHandler("reset", spy_bot.reset))
    dispatcher.add_handler(CommandHandler("history", spy_bot.history))
    dispatcher.add_handler(CommandHandler("tutorial", spy_bot.tutorial))

    dispatcher.add_handler(CallbackQueryHandler(spy_bot.button_handler))

    # on noncommand i.e message - echo the message on Telegram
    #dispatcher.add_handler(MessageHandler(Filters.photo, meow_bot.jpg2png))
    #dispatcher.add_handler(MessageHandler(Filters.all, meow_bot.jpg2png))
    #dispatcher.add_handler(MessageHandler(Filters.all, meow_bot.meow))
    #dispatcher.add_handler(MessageHandler(Filters.document.file_extension('txt'), meow_bot.meow))

    # Start the Bot
    updater.start_polling(clean=True)

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
