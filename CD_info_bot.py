#!/usr/bin/env python
# -*- coding: utf-8 -*-

import telegram as tg
from telegram import Update
import telegram.ext as tx
from telegram.ext import CallbackContext

from misc import parse_token, parse_id
import numpy as np
import json, os, signal, time

# import logging
# # Enable logging
# logging.basicConfig(
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
# )

# logger = logging.getLogger(__name__)

# Functions
def string_sum(string):
    return sum([ord(char) for char in string])

def string_hash(target, base):
    n = 13
    m = 1999
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

def split_question(str_list):
    whole_string = ' '.join(str_list)
    if '？' in whole_string:
        q_mark = '？'
    elif '?' in whole_string:
        q_mark = '?'
    else:
        return None, None
    qsn_opt = whole_string.split(q_mark)
    if len(qsn_opt) < 2 or qsn_opt[0] == '' or qsn_opt[1] == '':
        return None, None

    return qsn_opt[0], qsn_opt[1]

class BetGame:
    def __init__(self, host, description, options):
        self.host = host
        self.description = description
        self.options = dict(zip(options, [{'detail':{}, 'bet':0, 'odd':''}]*len(options)))
        self.total = 0
        self.closed = False
        self.markup = tg.InlineKeyboardMarkup([[tg.InlineKeyboardButton(callback_data=f'gamble {host} {opt} {col}', text=f'{col}') for col in [opt,1,5,10,50]] for opt in self.options])

    def stake_on(self, gamer, option, wager):
        if self.closed or option not in self.options:
            return None
        gamer = str(gamer)
        if gamer in self.options[option]['detail']:
            self.options[option]['detail'][gamer] += wager
        else:
            self.options[option]['detail'][gamer] = wager
        self.options[option]['bet'] += wager
        self.total += wager
        for opt in self.options:
            if self.options[opt]['bet'] > 0:
                self.options[opt]['odd'] = '%.3f'%(self.total/self.options[opt])

    def get_display(self):
        return self.description
                + ''.join([f'\n{opt}: {self.options[opt]['bet']} ({self.options[opt]['odd']})' for opt in self.options])
                , None if self.closed else self.markup

    def close(self):
        self.closed = True

    def settle(self, outcome):
        changes = {}
        for gamer in self.options[outcome]['detail']:
            changes[gamer] = int(self.total*self.options[outcome]['detail'][gamer]/self.options[outcome]['bet'])
        return changes


# Bot class
class CDInfoBot:
    def __init__(self, bot_token, bot_owner, bot_name, balance_file):
        self.token = bot_token
        self.owner = bot_owner
        self.name = bot_name
        self.balance_file = balance_file
        self.error_reply = ['🤯','😐']
        self.sorry_reply = ['🍑','🍓','🍎','🍊','🥭','🍍','🍅','🍈','🍋','🍐']
        self.envelopes = []
        self.user_balance = {}
        self.bet_games = {}
        self.p_possi = 25
        self.p_mean = 4
        self.p_std = 2

        self.updater = tx.Updater(self.token, use_context=True)
        dpr = self.updater.dispatcher
        #--------------------------------------------------------
        dpr.add_handler(tx.CommandHandler('start',  self.start))
        dpr.add_handler(tx.CommandHandler('choose', self.choose))
        dpr.add_handler(tx.CommandHandler('random', self.random))
        dpr.add_handler(tx.CommandHandler('tell',   self.tell))
        dpr.add_handler(tx.CommandHandler('tells',  self.tells))
        dpr.add_handler(tx.CommandHandler('shuffle',self.shuffle))
        dpr.add_handler(tx.CommandHandler('pair',   self.pair))
        dpr.add_handler(tx.CommandHandler('count',  self.count, run_async=True))
        #--------------------------------------------------------
        dpr.add_handler(tx.CommandHandler('balance',self.balance))
        dpr.add_handler(tx.MessageHandler(tx.Filters.all, self.show))
        dpr.add_handler(tx.CallbackQueryHandler(self.envelope, pattern='envelope'))
        dpr.add_handler(tx.CommandHandler('dice',   self.dice,  run_async=True))
        dpr.add_handler(tx.CommandHandler('gamble', self.gamble))
        dpr.add_handler(tx.CallbackQueryHandler(self.gamble_action, pattern='gamble'))
        #--------------------------------------------------------
        dpr.add_handler(tx.CommandHandler('sleep',  self.sleep))
        dpr.add_handler(tx.CommandHandler('status', self.status))
        dpr.add_handler(tx.CommandHandler('clear',  self.clear))
        dpr.add_handler(tx.CommandHandler('param',  self.param))
        dpr.add_handler(tx.CommandHandler('save',   self.save))
        dpr.add_handler(tx.CommandHandler('reward', self.reward))
        #--------------------------------------------------------
        print(f"[{self.name} handler ready]")

        try:
            self.user_balance = json.load(open(self.balance_file, 'r', encoding='utf8'))
            print(f"[{self.name} load balances]")
        except:
            print(f"[{self.name} no balances]")

    def run(self):
        self.updater.start_polling(poll_interval=1, clean=True)
        print(f"[{self.name} running]")
        self.updater.idle()
        print(f"[{self.name} terminated]")

# private functions        
####################################################################################

    def _valid_update(self, update):
        if update.message is None:
            return False
        else:
            print(update.message.from_user.full_name, ':', update.message.text)
            return True

    def _reply(self, update, text, **kwargs):
        update.message.reply_text(text)
        print(self.name, ':', text)

    def _reply_owner(self, update, text, **kwargs):
        update.message.bot.send_message(chat_id=self.owner, text=text)
        print(self.name, ':', text)

    def _balance_change(self, user_id, change):
        id_str = str(user_id)
        if change >= 0:
            if id_str in self.user_balance:
                self.user_balance[id_str] += change
            else:
                self.user_balance[id_str] = change
            return True
        else:
            if id_str in self.user_balance and self.user_balance[id_str] >= -change:
                self.user_balance[id_str] += change
                return True
            else:
                return False

# question
####################################################################################

# Command Handler: /start
    def start(self, update: Update, context: CallbackContext) -> None:
        self._reply(update, "嗨？")

# Command Handler: /choose
    def choose(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        if len(context.args) < 2:
            self._reply(update, self.error_reply[len(context.args)])
        else:
            result = old_determine(context.args)
            self._reply(update, result)

# Command Handler: /random
    def random(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        if len(context.args) < 2:
            self._reply(update, self.error_reply[len(context.args)])
        else:
            result = np.random.choice(context.args)
            self._reply(update, result)

# Command Handler: /tell
    def tell(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        question, options = split_question(context.args)
        if question is None or options is None:
            self._reply(update, self.error_reply[0])
            return
        options = options.split()
        if len(options) < 1:
            self._reply(update, self.error_reply[0])
        else:
            result = determine(options, question)
            self._reply(update, result)

# Command Handler: /tells
    def tells(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        question, options = split_question(context.args)
        if question is None or options is None:
            self._reply(update, self.error_reply[0])
            return
        options = options.split()
        if len(options) < 1:
            self._reply(update, self.error_reply[0])
        else:
            result = determine(options, question, sort=True)
            self._reply(update, result)    

# Command Handler: /shuffle
    def shuffle(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        if len(context.args) < 2:
            self._reply(update, self.error_reply[len(context.args)])
        else:
            np.random.shuffle(context.args)
            result = ' '.join(context.args)
            self._reply(update, result)

# Command Handler: /pair
    def pair(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return 
        source, target = split_question(context.args)
        if source is None or target is None:
            self._reply(update, self.error_reply[0])
            return
        source = source.split()
        target = target.split()
        if len(source) <= len(target):
            np.random.shuffle(target)
        else:
            target = target * (len(source)//len(target)+1)
            np.random.shuffle(target)
        result = ''.join([ '\n'+src+' - '+tar for src,tar in zip(source, target)])
        self._reply(update, result)

# Command Handler: /count
    def count(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        if len(context.args) < 1 or not str.isdigit(context.args[0]):
            self._reply(update, self.error_reply[0])
            return
        cd_time = int(context.args[0])
        if cd_time <= 0 or cd_time > 20:
            self._reply(update, self.error_reply[1])
            return
        count_message = update.message.reply_text(f"⏱ {context.args[0]}")
        while cd_time:
            time.sleep(1)
            cd_time -= 1
            update.message.bot.edit_message_text(chat_id=update.message.chat.id,
                                                 message_id=count_message.message_id,
                                                 text=f"⏱ {cd_time}")
        self._reply(update, "GO GO 🤩")

# finance
####################################################################################

# Command Handler: /balance
    def balance(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        id_str = str(update.message.from_user.id)
        if id_str in self.user_balance:
            balance = "{:,}".format(self.user_balance[id_str])
            self._reply(update, f"{update.message.from_user.full_name} 擁有{balance}顆 島幣")
        else:
            self._reply(update, f"{update.message.from_user.full_name} 擁有0顆 島幣")

# Message Handler: show
    def show(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        if update.message.chat.type != 'private' and np.random.randint(0,self.p_possi) == 0:
            money_str = str(round(np.random.normal(self.p_mean,self.p_std)))
            keyboard = [[tg.InlineKeyboardButton(callback_data=f'envelope{money_str}', text='領取🧧')]]
            reply_markup = tg.InlineKeyboardMarkup(keyboard)
            update.message.bot.send_message(chat_id=update.message.chat_id, reply_markup=reply_markup, text="搶紅包囉！")

# Callback Query Handler: envelope
    def envelope(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        if query.message.message_id not in self.envelopes:
            query.answer(text="搶到啦😁")
            money = int(query.data.replace('envelope',''))
            if money <= 0:
                query.edit_message_text(f"{query.from_user.full_name} 收到一顆 {np.random.choice(self.sorry_reply)}")
            else:
                money_str = "{:,}".format(money)
                query.edit_message_text(f"{query.from_user.full_name} 收到{money_str}顆 島幣")
                self._balance_change(query.from_user.id, money)
            self.envelopes.append(query.message.message_id)
        else:
            query.answer(text="沒搶到🙁")

# Command Handler: /dice
    def dice(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        if len(context.args) == 0:
            update.message.reply_dice(emoji=tg.constants.DICE_DICE)
            return
        if len(context.args) < 2 or not str.isdigit(context.args[0]) or not str.isdigit(context.args[1]):
            self._reply(update, self.error_reply[0])
            return
        guess = int(context.args[0])
        if guess <= 0 or guess > 6:
            self._reply(update, "就這麼想輸嗎？🤔")
            return

        user = update.message.from_user
        wager = int(context.args[1])
        if not self._balance_change(user.id, -wager):
            self._reply(update, "錢不夠耶😶")
            return

        dice_message = update.message.reply_dice(emoji=tg.constants.DICE_DICE)
        time.sleep(4)
        if guess == dice_message.dice.value:
            self._reply(update, f"猜中了😮 {user.full_name} 贏得{wager*5}顆 島幣")
            self._balance_change(user.id, wager*6) 
        else:
            self._reply(update, "沒猜中呦😐")

# Command Handler: /gamble
    def gamble(self, update: Update, context: CallbackContext) -> None:
        m = update.message
        game_id = f'{m.chat.id}:{m.message_id}'
        self.bet_games[game_id] = BetGame(m.from_user.id, context.args[0], context.args[1:])

# Callback Query Handler: gamble_action
    def gamble_action(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        m = query.message
        game_id = f'{m.chat.id}:{m.message_id}'
        # TODO


# control
####################################################################################

# Command Handler: /sleep (owner only)
    def sleep(self, update: Update, context: CallbackContext) -> None:
        if update.message.from_user.id == self.owner:
            self.save(update, context)
            self._reply(update, '😴', )
            os.kill(os.getpid(), signal.SIGINT)

# Command Handler: /status (owner only)
    def status(self, update: Update, context: CallbackContext) -> None:
        if update.message.from_user.id == self.owner:
            self._reply_owner(update, f"envelopes: {len(self.envelopes)}")

# Command Handler: /clear (owner only)
    def clear(self, update: Update, context: CallbackContext) -> None:
        if update.message.from_user.id == self.owner:
            self.envelopes = []
            self._reply_owner(update, f"envelopes: {len(self.envelopes)}")

# Command Handler: /param (owner only)
    def param(self, update: Update, context: CallbackContext) -> None:
        if update.message.from_user.id == self.owner:
            if len(context.args) == 0:
                self._reply_owner(update, ''.join([f"\n{key} = {value}" for key,value in self.__dict__.items() if 'p_' in key]))
            elif len(context.args) == 1 and context.args[0] in self.__dict__:
                self._reply_owner(update, f"{context.args[0]} = {self.__dict__[context.args[0]]}")
            elif len(context.args) == 2 and context.args[0] in self.__dict__ and 'p_' in context.args[0]:
                self.__dict__[context.args[0]] = int(context.args[1])
                self._reply_owner(update, f"{context.args[0]} = {self.__dict__[context.args[0]]}")
            else:
                self._reply_owner(update, 'command error')

# Command Handler: /save (owner only)
    def save(self, update: Update, context: CallbackContext) -> None:
        if update.message.from_user.id == self.owner:
            balances_str = ''.join([f'\n{user} : {balance}' for user,balance in self.user_balance.items()])
            if balances_str:
                self._reply_owner(update, balances_str)
            with open(self.balance_file, 'w', encoding='utf8') as outfile:
                json.dump(self.user_balance, outfile, indent=4, ensure_ascii=False)

# Command Handler: /reward (owner only)
    def reward(self, update: Update, context: CallbackContext) -> None:
        if update.message.from_user.id == self.owner:
            if len(context.args) == 2 and context.args[0] in self.user_balance:
                try:
                    change = int(context.args[1])
                except:
                    self._reply_owner(update, 'command error')
                    return
                self._balance_change(context.args[0], change)
                self.save(update, context)
            else:
                self._reply_owner(update, 'command error')

#-------------------------------------------------------------------
#   main
#-------------------------------------------------------------------
def main():

    bot_list = (('token_CD_info_bot', 'Island Bot', 'island_balance.json'),
               ('token_Justa_test_bot', 'Test Bot', 'test_balance.json'))

    which = 0

    bot_token = parse_token(bot_list[which][0])
    if not bot_token:
        print("[bot token file not found]")
        return

    bot_owner = parse_id('id_justa')
    if not bot_owner:
        print("[owner id file not found]")
        return
    
    bot_name = bot_list[which][1]

    bot = CDInfoBot(bot_token=bot_token,
                    bot_owner=bot_owner,
                    bot_name=bot_name,
                    balance_file=bot_list[which][2])
    bot.run()

if __name__ == '__main__':
    main()