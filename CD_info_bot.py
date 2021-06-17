#!/usr/bin/env python
# -*- coding: utf-8 -*-

import telegram as tg
from telegram import Update
import telegram.ext as tx
from telegram.ext import CallbackContext

from parse import parse_token, parse_id
import numpy as np
import json, os, signal, time
# import logging
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

def wolfram_replace(string):
    return string.replace('+', '%2B').replace(',', '%2C').replace('=', '%3D').replace('/', '%2F')

# Sub class
class BetGame:
    def __init__(self, host, description, options):
        self.id = ''
        self.state = '下注中'
        self.host = host
        self.description = description
        self.options = dict(zip(options, [{'detail':{}, 'bet':0, 'odd':''} for _ in range(len(options))]))
        self.total = 0
        inline_keyboard = [[tg.InlineKeyboardButton(text=txt, callback_data=f"gamble:{opt}:{stk}") for txt,stk in [(opt+': 1',1),('3',3),('5',5),('10',10)]] for opt in self.options]
        inline_keyboard.append([tg.InlineKeyboardButton(text='收盤', callback_data='gamble')])
        self.markup = tg.InlineKeyboardMarkup(inline_keyboard)

        self.inputs = {}
        self.outputs = {}
        self.changes = {}

    def set_id(self, game_id):
        self.id = game_id
        self.description = f"{self.id}\n{self.description}"

    def get_header(self):
        return f"{self.description}\n---{self.state}---"

    def get_text(self):
        return f"{self.description}\n---{self.state}---"+''.join([f"\n{opt}: {self.options[opt]['bet']} ({self.options[opt]['odd']})" for opt in self.options])

    def get_button(self):
        return self.markup

    def stake(self, gamer, option, wager):
        if option not in self.options or self.state != '下注中':
            return
        gamer_id = str(gamer.id)
        if gamer_id in self.inputs:
            self.inputs[gamer_id] += wager
        else:
            self.inputs[gamer_id] = wager
        if gamer_id in self.options[option]['detail']:
            self.options[option]['detail'][gamer_id] += wager
        else:
            self.options[option]['detail'][gamer_id] = wager
        self.options[option]['bet'] += wager
        self.total += wager
        for opt in self.options:
            if self.options[opt]['bet'] > 0:
                self.options[opt]['odd'] = '%.3f'%(self.total/self.options[opt]['bet'])

    def close(self):
        if self.state != '下注中':
            return
        inline_keyboard = [[tg.InlineKeyboardButton(text=opt, callback_data=f"gamble:{opt}")] for opt in self.options]
        inline_keyboard.append([tg.InlineKeyboardButton(text='流局', callback_data='gamble:$draw$')])
        self.markup = tg.InlineKeyboardMarkup(inline_keyboard) 
        self.state = '已收盤'

    def settle(self, outcome):
        if self.state != '已收盤':
            return

        if outcome == '$draw$':
            self.state = '流局'
            self.markup = None
            return self.inputs, f"{self.id}\n莊家指定結果：流局"

        for gamer in self.options[outcome]['detail']:
            self.outputs[gamer] = int(self.total*self.options[outcome]['detail'][gamer]/self.options[outcome]['bet'])
        for gamer in self.inputs:
            out = self.outputs[gamer] if gamer in self.outputs else 0
            self.changes[gamer] = out - self.inputs[gamer]
        self.markup = None
        if self.changes:
            display = f"{self.id}\n莊家指定結果：{outcome}"+''.join([f"\n***{gamer_id[-4:]} {'贏了' if amount >= 0 else '輸了'}{abs(amount)}顆 島幣" for gamer_id,amount in self.changes.items()])
            self.state = '已結算'
        else:
            display = f"{self.id}\n莊家指定結果：{outcome}\n但好像沒有人下注欸😶"
            self.state = '流局'

        return self.outputs, display

    def reverse(self):
        if self.state != '已結算':
            return None
        return {gamer:-change for gamer,change in self.changes.items()}

    def check(self, gamer):
        gamer_id = str(gamer.id)
        record = ""
        if self.state == '下注中' or self.state == '已收盤':
            for opt in self.options:
                if gamer_id in self.options[opt]['detail']:
                    record += f"\n{opt}: {self.options[opt]['detail'][gamer_id]}"
        elif self.state == '流局':
            record = " "
        else:
            if gamer_id in self.changes:
                record += f"\n{'贏了' if self.changes[gamer_id] >= 0 else '輸了'} {abs(self.changes[gamer_id])}"

        if record:
            return self.get_header()+record+'\n'
        else:
            return ""

# Bot class
class CDInfoBot:
    def __init__(self, bot_token, bot_owner, bot_name, balance_file):
        self.token = bot_token
        self.owner = bot_owner
        self.name = bot_name
        self.balance_file = balance_file
        self.error_reply = ['🤯','😐','😐']
        self.sorry_reply = ['🍑','🍓','🍎','🍊','🥭','🍍','🍅','🍈','🍋','🍐']
        self.envelopes = []
        self.user_balance = {}
        self.bet_games = {}
        self.donate_list = {}
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
        dpr.add_handler(tx.CommandHandler('wolfram',self.wolfram))
        #--------------------------------------------------------
        dpr.add_handler(tx.CommandHandler('balance',self.balance))
        dpr.add_handler(tx.CommandHandler('send',   self.send))
        dpr.add_handler(tx.CommandHandler('allin',  self.allin))
        dpr.add_handler(tx.CommandHandler('donate', self.donate))
        dpr.add_handler(tx.CommandHandler('dice',   self.dice,  run_async=True))
        dpr.add_handler(tx.CommandHandler('gamble', self.gamble))
        #--------------------------------------------------------
        dpr.add_handler(tx.CommandHandler('sleep',  self.sleep))
        dpr.add_handler(tx.CommandHandler('status', self.status))
        dpr.add_handler(tx.CommandHandler('clear',  self.clear))
        dpr.add_handler(tx.CommandHandler('param',  self.param))
        dpr.add_handler(tx.CommandHandler('save',   self.save))
        dpr.add_handler(tx.CommandHandler('reward', self.reward))
        dpr.add_handler(tx.CommandHandler('reverse',self.reverse))
        #--------------------------------------------------------
        dpr.add_handler(tx.CallbackQueryHandler(self.query_handler))
        dpr.add_handler(tx.MessageHandler(tx.Filters.all, self.show))
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

    def _save(self):
        balances_str = '\n{'+','.join([f'\n    "{user}": {balance}' for user,balance in self.user_balance.items()])+'\n}'
        with open(self.balance_file, 'w', encoding='utf8') as outfile:
            json.dump(self.user_balance, outfile, indent=4, ensure_ascii=False)
        return balances_str

    def _balance_change(self, user_id, change):
        id_str = str(user_id)
        if change >= 0:
            if id_str in self.user_balance:
                self.user_balance[id_str] += change
            else:
                self.user_balance[id_str] = change
            self._save()
            return True
        else:
            if id_str in self.user_balance and self.user_balance[id_str] >= -change:
                self.user_balance[id_str] += change
                self._save()
                return True
            else:
                return False

    def _force_change(self, user_id, change):
        id_str = str(user_id)
        if id_str in self.user_balance:
            self.user_balance[id_str] += change
        else:
            self.user_balance[id_str] = change

    def _balance_changes(self, change_sheet):
        [self._balance_change(user_id, change) for user_id,change in change_sheet.items()]

    def _force_changes(self, change_sheet):
        [self._force_change(user_id, change) for user_id,change in change_sheet.items()]

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

# Command Handler: /wolfram
    def wolfram(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        result = "https://www.wolframalpha.com/input/?i="+'+'.join([wolfram_replace(s) for s in context.args])
        self._reply(update, result)

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

# Command Handler: /send
    def send(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        elif update.message.reply_to_message is None:
            self._reply(update, self.error_reply[0])
        elif not context.args or not str.isdigit(context.args[0]):
            self._reply(update, self.error_reply[0])
        else:
            amount = int(context.args[0])
            if amount <= 0:
                self._reply(update, self.error_reply[1])

            sender = update.message.from_user
            receiver = update.message.reply_to_message.from_user
            if not self._balance_change(sender.id, -amount):
                update.message.reply_text(f"{sender.full_name} 錢不夠喔😶")
                return
            self._balance_change(receiver.id, amount)
            update.message.bot.send_message(chat_id=update.message.chat.id,
                                            text=f"{sender.full_name} 送給 {receiver.full_name} {amount}顆 島幣")

# Command Handler: /allin
    def allin(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        elif update.message.reply_to_message is None:
            self._reply(update, self.error_reply[0])
        else:
            sender = update.message.from_user
            receiver = update.message.reply_to_message.from_user
            amount = self.user_balance[str(sender.id)]
            self._balance_change(sender.id, -amount)
            self._balance_change(receiver.id, amount)
            update.message.bot.send_message(chat_id=update.message.chat.id,
                                            text=f"{sender.full_name} 歐印 {receiver.full_name} {amount}顆 島幣")

# Command Handler: /donate
    def donate(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        elif update.message.reply_to_message is None:
            self._reply(update, self.error_reply[0])
        else:
            target = update.message.reply_to_message
            target_id = f"{target.chat.id}#{target.message_id}"
            if target_id in self.donate_list:
                return
            self.donate_list[target_id] = {'chat_id':0,'msg_id':0,'detail':{}}
            amount_button = tg.InlineKeyboardMarkup([[tg.InlineKeyboardButton(text=num, callback_data=f"donate:{num}") for num in ['1','3','5','10']]])
            reply_msg = target.reply_text(text="打賞！", reply_markup=amount_button)
            self.donate_list[target_id]['chat_id'] = reply_msg.chat.id
            self.donate_list[target_id]['msg_id'] = reply_msg.message_id

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
        if not self._valid_update(update):
            return
        if not context.args:
            records = '\n'.join([game.check(update.message.from_user) for game in self.bet_games.values()])
            if records:
                self._reply(update, records)
            else:
                self._reply(update, "沒有賭博記錄呦🤗")
            return
        if len(context.args) < 3:
            self._reply(update, self.error_reply[len(context.args)])
            return
        bet_game = BetGame(update.message.from_user, context.args[0], context.args[1:])
        game_msg = update.message.reply_text(text=bet_game.get_text(), reply_markup=bet_game.get_button())
        game_id = f'{game_msg.chat.id%10000}#{game_msg.message_id}'
        bet_game.set_id(game_id)
        self.bet_games[game_id] = bet_game
        game_msg.bot.edit_message_text( chat_id=game_msg.chat.id,
                                        message_id=game_msg.message_id,
                                        text=bet_game.get_text(),
                                        reply_markup=bet_game.get_button())

# Callback Query Handler: query_handler
    def query_handler(self, update: Update, context: CallbackContext) -> None:
        data = update.callback_query.data
        if data[:8] == 'envelope':
            self.open_envelope(update, context)
        elif data[:6] == 'gamble':
            self.gamble_action(update, context)
        elif data[:6] == 'donate':
            self.donate_handle(update, context)

# Callback Query Handler: open_envelope
    def open_envelope(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        if query.message.message_id not in self.envelopes:
            query.answer(text="搶到啦😁")
            money = int(query.data.split(':')[1])
            if money <= 0:
                query.edit_message_text(f"{query.from_user.full_name} 收到一顆 {np.random.choice(self.sorry_reply)}")
            else:
                money_str = "{:,}".format(money)
                query.edit_message_text(f"{query.from_user.full_name} 收到{money_str}顆 島幣")
                self._balance_change(query.from_user.id, money)
            self.envelopes.append(query.message.message_id)
        else:
            query.answer(text="沒搶到🙁")

# Callback Query Handler: gamble_action
    def gamble_action(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        game_id = f'{query.message.chat.id%10000}#{query.message.message_id}'
        if game_id not in self.bet_games:
            query.answer(text="無效賭局", show_alert=True)
            return
        game = self.bet_games[game_id]
        struct = query.data.split(':')
        gamer = query.from_user
        host = game.host
        act = len(struct)
        # betting
        if act == 3:
            stk = int(struct[2])
            if not self._balance_change(gamer.id, -stk):
                query.answer(text="錢不夠耶😶", show_alert=True)
            else:
                game.stake(gamer,struct[1],stk)
                query.answer(text="下注成功", show_alert=True)
                query.edit_message_text(text=game.get_text(), reply_markup=game.get_button())
        # close
        elif act == 1:
            if gamer != host:
                query.answer(text="你不是莊家😶", show_alert=True)
            else:
                game.close()
                query.answer(text="關閉賭局")
                query.edit_message_text(text=game.get_text(), reply_markup=game.get_button())
        # settle
        elif act == 2:
            if gamer != host:
                query.answer(text="你不是莊家😶", show_alert=True)
            else:
                outputs, changes_display = game.settle(struct[1])
                self._balance_changes(outputs)
                query.answer(text="結算成功")
                query.edit_message_text(text=game.get_text(), reply_markup=game.get_button())
                query.message.reply_text(changes_display)
        else:
            query.answer(text="系統錯誤", show_alert=True)

# Callback Query Handler: donate_handle
    def donate_handle(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        target = query.message.reply_to_message
        target_id = f"{target.chat.id}#{target.message_id}"
        if target_id not in self.donate_list:
            query.answer(text="不能抖了😶", show_alert=True)
            return
        donor = query.from_user.full_name
        amount = int(query.data.split(':')[1])
        if not self._balance_change(query.from_user.id, -amount):
            query.answer(text="錢不夠耶😶", show_alert=True)
            return
        self._balance_change(target.from_user.id, amount)
        query.answer(text="抖內成功", show_alert=True)
        donate = self.donate_list[target_id]
        if donor in donate['detail']:
            donate['detail'][donor] += amount
        else:
            donate['detail'][donor] = amount
        total = sum(self.donate_list[target_id]['detail'].values())
        amount_button = tg.InlineKeyboardMarkup([[tg.InlineKeyboardButton(text=num, callback_data=f"donate:{num}") for num in ['1','3','5','10']]])
        query.message.bot.edit_message_text(chat_id=donate['chat_id'],
                                            message_id=donate['msg_id'],
                                            text=''.join([f"\n{donor} 抖內{amount}顆島幣" for donor,amount in donate['detail'].items()])+f"\n-----\n此訊息獲得{total}顆 島幣",
                                            reply_markup=amount_button)

# Message Handler: show
    def show(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        if update.message.chat.type != 'private' and np.random.randint(0,self.p_possi) == 0:
            money_str = str(round(np.random.normal(self.p_mean,self.p_std)))
            keyboard = [[tg.InlineKeyboardButton(callback_data=f'envelope:{money_str}', text='領取🧧')]]
            reply_markup = tg.InlineKeyboardMarkup(keyboard)
            update.message.bot.send_message(chat_id=update.message.chat_id, reply_markup=reply_markup, text="搶紅包囉！")

# control (owner only)
####################################################################################

# Command Handler: /sleep
    def sleep(self, update: Update, context: CallbackContext) -> None:
        if update.message.from_user.id == self.owner:
            self.save(update, context)
            self._reply(update, '😴', )
            os.kill(os.getpid(), signal.SIGINT)

# Command Handler: /status
    def status(self, update: Update, context: CallbackContext) -> None:
        if update.message.from_user.id == self.owner:
            show = f"\nenvelopes: {len(self.envelopes)}"+\
                   f"\nbet_games: {len(self.bet_games)}\n"+\
                   '\n'.join([f"  {gid} {game.state}" for gid,game in self.bet_games.items()])+\
                   f"\ndonate_list: {len(self.donate_list)}"
            self._reply_owner(update, show)

# Command Handler: /clear
    def clear(self, update: Update, context: CallbackContext) -> None:
        if update.message.from_user.id == self.owner:
            self.envelopes = []
            for gid in list(self.bet_games):
                if self.bet_games[gid].state == '流局':
                    del self.bet_games[gid]

            for donate in self.donate_list.values():
                update.message.bot.edit_message_reply_markup(chat_id=donate['chat_id'],
                                                             message_id=donate['msg_id'],
                                                             reply_markup=None)
            self.donate_list = {}
            self.status(update, context)

# Command Handler: /param
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

# Command Handler: /save
    def save(self, update: Update, context: CallbackContext) -> None:
        if update.message.from_user.id == self.owner:
            balances_str = self._save()
            if balances_str:
                self._reply_owner(update, balances_str)

# Command Handler: /reward
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

# Command Handler: /reverse
    def reverse(self, update: Update, context: CallbackContext) -> None:
        if not context.args:
            self._reply_owner(update, 'command error')
        elif context.args[0] not in self.bet_games:
            self._reply_owner(update, 'no such game')
        else:
            game = self.bet_games[context.args[0]]
            re_changes = game.reverse()
            if re_changes:
                self._force_changes(re_changes)
                update.message.reply_text(f"{game.id}\n時光倒流"+''.join([f"\n***{gamer_id[-4:]} {'收回' if amount > 0 else '繳回'}{abs(amount)}顆 島幣" for gamer_id,amount in re_changes.items()]))
                del self.bet_games[context.args[0]]
            else:
                self._reply_owner(update, 'state error')

####################################################################################

def main():

    bot_list = (('token_CD_info_bot', 'Island Bot', 'balance_island.json'),
                ('token_CD_shad_bot', 'Shadow Bot', 'balance_shadow.json'))

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