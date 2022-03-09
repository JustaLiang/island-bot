#!/usr/bin/env python
# -*- coding: utf-8 -*-

import telegram as tg
from telegram import Update
from telegram import user
import telegram.ext as tx
from telegram.ext import CallbackContext

import numpy as np
import json, os, signal, time, sys
import pymongo

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from datetime import datetime
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

def cloth_check(cloth):
    valid = ""
    remain = ""
    for f in cloth:
        if f not in valid:
            valid += f
        else:
            remain += f
    if len(valid) >= 5:
        return True, remain
    else:
        return False, cloth

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
        self.description = f"{self.id[-7:]}\n{self.description}"

    def get_header(self):
        return f"{self.description}\n---{self.state}---"

    def get_text(self):
        return f"{self.description}\n---{self.state}---"+''.join([f"\n{opt}: {self.options[opt]['bet']} ({self.options[opt]['odd']})" for opt in self.options])

    def get_button(self):
        return self.markup

    def stake(self, gamer, option, wager):
        if option not in self.options or self.state != '下注中':
            return
        if gamer.id in self.inputs:
            self.inputs[gamer.id] += wager
        else:
            self.inputs[gamer.id] = wager
        if gamer.id in self.options[option]['detail']:
            self.options[option]['detail'][gamer.id] += wager
        else:
            self.options[option]['detail'][gamer.id] = wager
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
            display = f"{self.id}\n莊家指定結果：{outcome}"+''.join([f"\n***{str(gamer_id)[-4:]} {'贏了' if amount >= 0 else '輸了'}{abs(amount)}顆 島幣" for gamer_id,amount in self.changes.items()])
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
        record = ""
        if self.state == '下注中' or self.state == '已收盤':
            for opt in self.options:
                if gamer.id in self.options[opt]['detail']:
                    record += f"\n{opt}: {self.options[opt]['detail'][gamer.id]}"
        elif self.state == '流局':
            record = " "
        else:
            if gamer.id in self.changes:
                record += f"\n{'贏了' if self.changes[gamer.id] >= 0 else '輸了'} {abs(self.changes[gamer.id])}"

        if record:
            return self.get_header()+record+'\n'
        else:
            return ""

# Bot class
class CDInfoBot:
    def __init__(self, bot_profile):
        self.setup = False

        bot_info = json.load(open(bot_profile, 'r', encoding='utf8'))
        self.token = bot_info['token']
        self.owner = bot_info['owner']
        self.name = bot_info['name']
        self.error_reply = ["🤯","😐","😐"]
        self.sorry_reply = ["🍑","🍓","🍎","🍊","🥭","🍍","🍅","🍈","🍋","🍐"]
        self.bet_games = {}
        self.dev = bot_info['dev']
        if self.dev:
            self._valid_type = self._dev_valid_type
            self.p_possi = 1
            self.p_mean = 0
            self.p_std = 4
        else:
            self._valid_type = self._norm_valid_type            
            self.p_possi = 50
            self.p_mean = 4
            self.p_std = 2

        # database
        self.client = pymongo.MongoClient("mongodb://localhost:27017")
        self.db = self.client.get_database(self.name)
        # if self.dev:
        #     self.db.drop_collection('balance')
        #     self.db.drop_collection('buffer')
        self.db_balance = self.db.get_collection('balance')
        self.db_buffer = self.db.get_collection('buffer')
        print(f"[{self.name} setup database]")

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
        dpr.add_handler(tx.CommandHandler('dice',   self.dice,  run_async=True))
        dpr.add_handler(tx.CommandHandler('gamble', self.gamble))
        dpr.add_handler(tx.CommandHandler('fruit',  self.fruit))
        dpr.add_handler(tx.CommandHandler('cloth',  self.cloth))
        dpr.add_handler(tx.CommandHandler('throw',  self.throw))
        dpr.add_handler(tx.CommandHandler('sell',   self.sell))
        dpr.add_handler(tx.CommandHandler('buy',    self.buy))
        #--------------------------------------------------------
        dpr.add_handler(tx.CommandHandler('sleep',  self.sleep))
        dpr.add_handler(tx.CommandHandler('status', self.status))
        dpr.add_handler(tx.CommandHandler('clear',  self.clear))
        dpr.add_handler(tx.CommandHandler('param',  self.param))
        dpr.add_handler(tx.CommandHandler('reverse',self.reverse))
        dpr.add_handler(tx.CommandHandler('mint',   self.mint))
        # dpr.add_handler(tx.CommandHandler('load',   self.load))
        #--------------------------------------------------------
        dpr.add_handler(tx.CallbackQueryHandler(self.query_handler))
        dpr.add_handler(tx.MessageHandler(tx.Filters.all, self.show))
        self.bot = dpr.bot
        self.me = self.bot.getMe()
        self.db_balance.delete_one({'user': self.me.id})
        print(f"[{self.name} handler ready]")

        self.setup = True

    def run(self):
        if self.setup:
            self.updater.start_polling(poll_interval=1, clean=True)
            print(f"[{self.name} running]")
            self.updater.idle()
            print(f"[{self.name} terminated]")
        else:
            print(f"[{self.name} terminated]")

# private functions
####################################################################################

    def _valid_update(self, update):
        if update.message is None:
            return False
        else:
            print(update.message.from_user.full_name, ':', update.message.text)
            return True

    def _dev_valid_type(self, msg_type):
        return msg_type == 'private'

    def _norm_valid_type(seld, msg_type):
        return msg_type != 'private'

    def _reply(self, update, text, **kwargs):
        update.message.reply_text(text)
        print(self.name, ':', text)

    def _reply_owner(self, update, text, **kwargs):
        self.bot.send_message(chat_id=self.owner, text=text)
        print(self.name, ':', text)

    def _get_user_info(self, user_id: int):
        user_info = self.db_balance.find_one({'user': user_id})
        if user_info is None:
            self.db_balance.insert_one({'user': user_id, 'balance': 0, 'fruit': "", 'cloth': ""})
            return self.db_balance.find_one({'user': user_id})
        else:
            return user_info

    def _balance_change(self, user_id: int, change: int):
        user_info = self._get_user_info(user_id)
        if change < 0 and user_info['balance'] + change < 0:
            return False
        else:
            self.db_balance.update_one({'user': user_id}, {'$inc': {'balance': change}})
            return True

    def _force_change(self, user_id: int, change: int):
        if None is self.db_balance.find_one_and_update({'user': user_id}, {'$inc': {'balance': change}}):
            self.db_balance.insert_one({'user': user_id, 'balance': change, 'fruit': "", 'cloth': ""})

    def _fruit_transfer(self, sender_id: int, receiver_id: int, fruit: str):
        sender_info = self._get_user_info(sender_id)
        receiver_info = self._get_user_info(receiver_id)
        if fruit in sender_info['fruit'] and len(receiver_info['fruit']) < 5:
            fruit_after = sender_info['fruit'].replace(fruit, '', 1)
            self.db_balance.update_one({'user': sender_id}, {'$set': {'fruit': fruit_after}})
            if receiver_id != self.me.id:
                fruit_after = receiver_info['fruit'] + fruit
                self.db_balance.update_one({'user': receiver_id}, {'$set': {'fruit': fruit_after}})
            return True
        else:
            return False

    def _fruit_change(self, user_id: int, fruit: str, inc: bool):
        user_info = self._get_user_info(user_id)
        if inc:
            if len(user_info['fruit']) >= 5:
                return False
            else:
                fruit_after = user_info['fruit'] + fruit
                self.db_balance.update_one({'user': user_id}, {'$set': {'fruit': fruit_after}})
                return True
        else:
            if fruit not in user_info['fruit']:
                return False
            else:
                fruit_after = user_info['fruit'].replace(fruit, '', 1)
                self.db_balance.update_one({'user': user_id}, {'$set': {'fruit': fruit_after}})
                return True

    def _fruit_pop(self, user_id: int):
        user_info = self._get_user_info(user_id)
        fruits_after = user_info['fruit']
        if fruits_after:
            fruit = np.random.choice(list(fruits_after))
            fruit_after = fruits_after.replace(fruit, '', 1)
            self.db_balance.update_one({'user': user_id}, {'$set': {'fruit': fruit_after}})
            return fruit
        else:
            return ""

    def _balance_changes(self, change_sheet):
        [self._balance_change(user_id, change) for user_id,change in change_sheet.items()]

    def _force_changes(self, change_sheet):
        [self._force_change(user_id, change) for user_id,change in change_sheet.items()]

    def _sentence_announce(self, user):
        profile = user.get_profile_photos()
        file = None
        for p in profile.photos:
            try:
                file = self.bot.get_file(p[0])
                psize = (p[0]["width"], p[0]["height"])
                break
            except tg.error.TelegramError:
                pass
        if file is not None:
            bio = BytesIO(file.download_as_bytearray())
            img = Image.open(bio)
            img = img.convert("L").convert("RGB")
        else:
            bio = BytesIO()
            psize = (160,160)
            img = Image.new("RGB", psize)

        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype("Oswald-Bold.ttf", psize[0]//8)
        timestamp = datetime.now().strftime("%Y/%m/%d\n%H:%M:%S")
        draw.multiline_text(xy=(psize[0]//2,psize[1]//2),
                            text=f"{timestamp}\n{user.full_name}\nFINED 50 ISD",
                            fill=(255,0,0), font=font, anchor="mm",
                            spacing=psize[0]//16, align="center")
        bio.seek(0)
        img.save(bio, "JPEG")
        bio.seek(0)
        return bio

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
        user_info = self._get_user_info(update.message.from_user.id)
        if user_info['balance'] >= 0:
            balance = "{:,}".format(user_info['balance'])
            self._reply(update, f"{update.message.from_user.full_name} 擁有{balance}顆 島幣")
        else:
            balance = "{:,}".format(-user_info['balance'])
            self._reply(update, f"{update.message.from_user.full_name} 欠債{balance}顆 島幣")

# Command Handler: /send
    def send(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        if update.message.reply_to_message is None or not context.args:
            self._reply(update, self.error_reply[0])
            return
        sender = update.message.from_user
        receiver = update.message.reply_to_message.from_user
        # send ISD coin
        if str.isdigit(context.args[0]):
            amount = int(context.args[0])
            if amount <= 0:
                self._reply(update, self.error_reply[1])
                return

            if not self._balance_change(sender.id, -amount):
                update.message.reply_text(f"{sender.full_name} 錢不夠喔😶")
                return
            if receiver.id != self.me.id:
                self._balance_change(receiver.id, amount)
                self.bot.send_message(chat_id=update.message.chat.id,
                    text=f"{sender.full_name} 送給 {receiver.full_name} {amount}顆 島幣")
            else:
                self.bot.send_message(chat_id=update.message.chat.id,
                    text=f"小島不需要錢喔 😎")
                keyboard = [[tg.InlineKeyboardButton(callback_data=f'envelope:{amount}', text='領取🧧')]]
                reply_markup = tg.InlineKeyboardMarkup(keyboard)
                self.bot.send_message(chat_id=update.message.chat_id, reply_markup=reply_markup, text="搶紅包囉！")        
        # send fruit
        else:
            valid_fruits = ""
            for fruit in context.args[0]:
                if self._fruit_transfer(sender.id, receiver.id, fruit):
                    valid_fruits += fruit
            if valid_fruits:
                self.bot.send_message(chat_id=update.message.chat.id,
                    text=f"{sender.full_name} 送給 {receiver.full_name} {valid_fruits}")    
            else:
                self._reply(update, "來亂的嗎🤨")
                return
            if receiver.id == self.me.id:
                if len(valid_fruits) == 1:
                    update.message.reply_text(f"謝謝 {sender.full_name}！\n好吃")
                    self.bot.send_message(chat_id=update.message.chat.id, text="😋")
                elif len(valid_fruits) == 2:
                    update.message.reply_text(f'謝謝 {sender.full_name}！\n好好吃')
                    self.bot.send_message(chat_id=update.message.chat.id, text="😋")
                elif len(valid_fruits) == 3:
                    update.message.reply_text(f'謝謝 {sender.full_name}！\n好多好多')
                    self.bot.send_message(chat_id=update.message.chat.id, text="🤩")
                elif len(valid_fruits) == 4:
                    update.message.reply_text(f'謝謝 {sender.full_name}！\n好幸福')
                    self.bot.send_message(chat_id=update.message.chat.id, text="🥰")
                elif len(valid_fruits) == 5:
                    update.message.reply_text(f'謝謝 {sender.full_name}！\n幸福到升天')
                    self.bot.send_message(chat_id=update.message.chat.id, text="😇")
                    self.bot.send_message(chat_id=update.message.chat.id, text="(暫停服務)")
                    time.sleep(60)
                    self.bot.send_message(chat_id=update.message.chat.id, text="我回來了🙂")

# Command Handler: /allin
    def allin(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        elif update.message.reply_to_message is None:
            self._reply(update, self.error_reply[0])
        else:
            sender = update.message.from_user
            receiver = update.message.reply_to_message.from_user
            sender_info = self._get_user_info(sender.id)
            amount = sender_info['balance']
            if amount <= 0:
                update.message.reply_text(f"{sender.full_name} 錢不夠喔😶")
                return
            self._balance_change(sender.id, -amount)
            self._balance_change(receiver.id, amount)
            self.bot.send_message(  chat_id=update.message.chat.id,
                                    text=f"{sender.full_name} 歐印 {receiver.full_name} {amount}顆 島幣")

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
        if wager <= 0:
            self._reply(update, self.error_reply[1])
            return
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
        game_id = f'{game_msg.chat.id}#{game_msg.message_id}'
        bet_game.set_id(game_id)
        self.bet_games[game_id] = bet_game
        game_msg.bot.edit_message_text( chat_id=game_msg.chat.id,
                                        message_id=game_msg.message_id,
                                        text=bet_game.get_text(),
                                        reply_markup=bet_game.get_button())

# Command Handler: /fruit
    def fruit(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        user_info = self._get_user_info(update.message.from_user.id)
        if len(user_info['fruit']) > 0:
            self._reply(update, f"{update.message.from_user.full_name} 的水果庫:\n{user_info['fruit']}")
        else:
            self._reply(update, f"{update.message.from_user.full_name} 想要水果🤤")      

# Command Handler: /cloth
    def cloth(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        if update.message.reply_to_message is None:
            target = update.message.from_user
        else:
            target = update.message.reply_to_message.from_user

        user_info = self._get_user_info(target.id)

        if user_info['cloth']:
            self._reply(update, f"{target.full_name} 衣服上的水果:\n{user_info['cloth']}")
        else:
            self._reply(update, f"{target.full_name} 品行優良😌") 

# Command Handler: /throw
    def throw(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        elif update.message.reply_to_message is None:
            self._reply(update, self.error_reply[0])
        else:
            sender = update.message.from_user
            receiver = update.message.reply_to_message.from_user
            throwing = self._fruit_pop(sender.id)
            if not throwing:
                update.message.reply_text(f"{sender.full_name} 沒有水果😶")
                return
            if receiver.id == self.me.id:
                self._reply(update, "小島怎麼了🥺")
                return
            receiver_info = self._get_user_info(receiver.id)
            receiver_cloth = receiver_info['cloth'] + throwing
            if sender.id == receiver.id:
                update.message.reply_text(f"{sender.full_name} 自砸了一顆 {throwing} 哇嗚😯")
            else:  
                update.message.reply_text(f"{sender.full_name} 向 {receiver.full_name} 砸了一顆 {throwing}")
            penalty, remain = cloth_check(receiver_cloth)
            self.db_balance.update_one({'user': receiver.id}, {'$set': {'cloth': remain}})
            if penalty:
                self._force_change(receiver.id, -50)
                msg = self.bot.send_photo(chat_id=update.message.chat.id,
                                        photo=self._sentence_announce(receiver),
                                        caption=f"{receiver.full_name} 言行多次令人不適\n罰款 50 顆 島幣")
                self.bot.pin_chat_message(chat_id=update.message.chat.id,
                                        message_id=msg.message_id)

# Command Handler: /sell
    def sell(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        if len(context.args) != 2 or not str.isdigit(context.args[1]):
            self._reply(update, self.error_reply[0])
            return
        seller = update.message.from_user
        valid_fruits = ""
        for fruit in context.args[0]:
            if self._fruit_change(seller.id, fruit, False):
                valid_fruits += fruit
        if not valid_fruits:
            self._reply(update, "來亂的嗎🤨")
            return
        price = context.args[1]
        keyboard = [[tg.InlineKeyboardButton(callback_data=f'sell:{seller.id}:{valid_fruits}:{price}', text=f'${price} 買入')]]
        reply_markup = tg.InlineKeyboardMarkup(keyboard)
        msg = self.bot.send_message(
            chat_id=update.message.chat_id,
            reply_markup=reply_markup,
            text=f"{seller.full_name}出售水果！\n{valid_fruits}")
        self.db_buffer.insert_one({'chat':msg.chat_id, 'msg': msg.message_id})

# Command Handler: /buy
    def buy(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        if len(context.args) != 2 or not str.isdigit(context.args[1]):
            self._reply(update, self.error_reply[0])
            return
        buyer = update.message.from_user
        valid_fruits = ""
        for fruit in context.args[0]:
            if fruit in self.sorry_reply:
                valid_fruits += fruit
        if not valid_fruits:
            self._reply(update, "來亂的嗎🤨")
            return
        price = context.args[1]
        if not self._balance_change(buyer.id, -int(price)):
            self._reply(update, "錢不夠耶😶")
            return
        keyboard = [[tg.InlineKeyboardButton(callback_data=f'buy:{buyer.id}:{valid_fruits}:{price}', text=f'${price} 賣出')]]
        reply_markup = tg.InlineKeyboardMarkup(keyboard)
        msg = self.bot.send_message(
            chat_id=update.message.chat_id,
            reply_markup=reply_markup,
            text=f"{buyer.full_name}想買水果！\n{valid_fruits}")
        self.db_buffer.insert_one({'chat':msg.chat_id, 'msg': msg.message_id})

## query_handler
####################################################################################

# Callback Query Handler: query_handler
    def query_handler(self, update: Update, context: CallbackContext) -> None:
        data = update.callback_query.data
        if data[:8] == 'envelope':
            self.open_envelope(update, context)
        elif data[:6] == 'gamble':
            self.gamble_action(update, context)
        elif data[:4] == 'sell':
            self.process_sell(update, context)
        elif data[:3] == 'buy':
            self.process_buy(update, context)

# Callback Query Handler: open_envelope
    def open_envelope(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        envelope = {'chat': query.message.chat_id, 'msg': query.message.message_id}
        if self.db_buffer.find_one(envelope) is None:
            query.answer(text="沒搶到🙁")
            return
        money = int(query.data.split(':')[1])
        user_id = query.from_user.id
        if money <= 0:
            fruit = np.random.choice(self.sorry_reply)
            if self._fruit_change(user_id, fruit, True):
                query.answer(text="搶到啦😁")
            else:
                query.answer(text="水果太多囉😶")
                return
            query.edit_message_text(f"{query.from_user.full_name} 收到一顆 {fruit}")
        else:
            money_str = "{:,}".format(money)
            self._balance_change(query.from_user.id, money)
            query.edit_message_text(f"{query.from_user.full_name} 收到{money_str}顆 島幣")
        self.db_buffer.delete_one(envelope)
        

# Callback Query Handler: gamble_action
    def gamble_action(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        game_id = f'{query.message.chat.id}#{query.message.message_id}'
        if game_id not in self.bet_games:
            query.answer(text="無效賭局", show_alert=True)
            return
        game = self.bet_games[game_id]
        gamble_struct = query.data.split(':')
        gamer = query.from_user
        host = game.host
        act = len(gamble_struct)
        # betting
        if act == 3:
            stk = int(gamble_struct[2])
            if not self._balance_change(gamer.id, -stk):
                query.answer(text="錢不夠耶😶", show_alert=True)
            else:
                game.stake(gamer, gamble_struct[1], stk)
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
                outputs, changes_display = game.settle(gamble_struct[1])
                self._balance_changes(outputs)
                query.answer(text="結算成功")
                query.edit_message_text(text=game.get_text(), reply_markup=game.get_button())
                query.message.reply_text(changes_display)
        else:
            query.answer(text="系統錯誤", show_alert=True)


    def process_sell(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        envelope = {'chat': query.message.chat_id, 'msg': query.message.message_id}
        if self.db_buffer.find_one(envelope) is None:
            query.answer(text="別人成交了🙁")
            return
        sell_struct = query.data.split(':')
        if len(sell_struct) != 4:
            print("error:", query.data)
            return
        seller_id = int(sell_struct[1])
        fruits = sell_struct[2]
        price = int(sell_struct[3])
        buyer = query.from_user
        buyer_info = self._get_user_info(buyer.id)
        fruit_after = buyer_info['fruit'] + fruits
        if len(fruit_after) > 5:
            query.answer(text="水果太多囉😶")
            return
        if seller_id != buyer.id:
            # buyer get fruit lose coin
            if not self._balance_change(buyer.id, -price):
                query.answer(text="錢不夠耶😶")
                return
            for f in fruits:
                self._fruit_change(buyer.id, f, True)
            # seller get coin
            self._balance_change(seller_id, price)

            self.db_buffer.delete_one(envelope)
            query.edit_message_text(f"{buyer.full_name}\n花 {price} 島幣\n買了 {fruits}")
            query.answer(text=f"買了{fruits}！ 🥳", show_alert=True)
        else:
            # return fruits
            for f in fruits:
                self._fruit_change(buyer.id, f, True)
            self.db_buffer.delete_one(envelope)
            query.answer(text=f"已撤回賣單")
            query.delete_message()

# Callback Query Handler: process_buy
    def process_buy(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        envelope = {'chat': query.message.chat_id, 'msg': query.message.message_id}
        if self.db_buffer.find_one(envelope) is None:
            query.answer(text="別人成交了🙁")
            return
        buy_struct = query.data.split(':')
        if len(buy_struct) != 4:
            print("error:", query.data)
            return
        buyer_id = int(buy_struct[1])
        fruits = buy_struct[2]
        price = int(buy_struct[3])
        seller = query.from_user
        buyer_info = self._get_user_info(buyer_id)
        fruit_after = buyer_info['fruit'] + fruits
        seller_fruits = self._get_user_info(seller.id)['fruit']
        if seller.id != buyer_id:
            if len(fruit_after) > 5:
                query.answer(text="買家水果太多囉😶")
                return
            for f in fruits:
                if f not in seller_fruits:
                    query.answer(text=f"你沒有{f}喔😶")
                    return
            # buyer get fruit
            for f in fruits:
                self._fruit_change(buyer_id, f, True)
            # seller get coin and lost fruit
            self._balance_change(seller.id, price)
            for f in fruits:
                self._fruit_change(seller.id, f, False)

            self.db_buffer.delete_one(envelope)
            query.edit_message_text(f"{seller.full_name}\n賣出 {fruits}\n賺了 {price} 島幣")
            query.answer(text=f"賺取 {price} 島幣！ 🥳", show_alert=True)
        else:
            # return coin
            self._balance_change(seller.id, price)
            self.db_buffer.delete_one(envelope)
            query.answer(text=f"已撤回買單")
            query.delete_message()

# Message Handler: show
    def show(self, update: Update, context: CallbackContext) -> None:
        if not self._valid_update(update):
            return
        if self._valid_type(update.message.chat.type) and np.random.randint(0,self.p_possi) == 0:
            money_str = str(round(np.random.normal(self.p_mean,self.p_std)))
            keyboard = [[tg.InlineKeyboardButton(callback_data=f'envelope:{money_str}', text='領取🧧')]]
            reply_markup = tg.InlineKeyboardMarkup(keyboard)
            msg = self.bot.send_message(chat_id=update.message.chat_id, reply_markup=reply_markup, text="搶紅包囉！")
            self.db_buffer.insert_one({'chat': msg.chat_id, 'msg': msg.message_id})

# control (owner only)
####################################################################################

# Command Handler: /sleep
    def sleep(self, update: Update, context: CallbackContext) -> None:
        if update.message.from_user.id == self.owner:
            self._reply(update, '😴', )
            os.kill(os.getpid(), signal.SIGINT)

# Command Handler: /status
    def status(self, update: Update, context: CallbackContext) -> None:
        if update.message.from_user.id == self.owner:
            show = f"\nbet_games: {len(self.bet_games)}\n"+\
                   '\n'.join([f"  {gid} {game.state}" for gid,game in self.bet_games.items()])
            self._reply_owner(update, show)

# Command Handler: /clear
    def clear(self, update: Update, context: CallbackContext) -> None:
        if update.message.from_user.id == self.owner:
            for gid in list(self.bet_games):
                if self.bet_games[gid].state == '流局':
                    del self.bet_games[gid]
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

# Command Handler: /reverse
    def reverse(self, update: Update, context: CallbackContext) -> None:
        if update.message.from_user.id == self.owner:
            if not context.args:
                self._reply_owner(update, 'command error')
            elif context.args[0] not in self.bet_games:
                self._reply_owner(update, 'no such game')
            else:
                game = self.bet_games[context.args[0]]
                re_changes = game.reverse()
                if re_changes:
                    self._force_changes(re_changes)
                    update.message.reply_text(f"{game.id}\n時光倒流"+''.join([f"\n***{str(gamer_id)[-4:]} {'收回' if amount > 0 else '繳回'}{abs(amount)}顆 島幣" for gamer_id,amount in re_changes.items()]))
                    del self.bet_games[context.args[0]]
                else:
                    self._reply_owner(update, 'state error')

# Command Handler: /mint
    def mint(self, update: Update, context: CallbackContext) -> None:
        if self.dev and update.message.from_user.id == self.owner:
            for c in context.args:
                if str.isdigit(c):
                    self.db_balance.update_one({'user': self.owner}, {'$set': {'balance': int(c)}})
                else:
                    self.db_balance.update_one({'user': self.owner}, {'$set': {'fruit': c}})
            self.balance(update, context)
            self.fruit(update, context)

# Command Handler: /load
    # def load(self, update: Update, context: CallbackContext) -> None:
    #     if update.message.from_user.id == self.owner:
    #         balance_json = json.load(open("island_balance.json", 'r', encoding='utf8'))
    #         for user_id, fruit in balance_json['fruit'].items():
    #             user_info = self._get_user_info(int(user_id))
    #             exceed = len(fruit) - len(user_info['fruit'])
    #             print(exceed)
    #             return_coin = 0
    #             if exceed > 0:
    #                 return_coin = exceed * 5
    #             self.db_balance.update_one({'user': int(user_id)}, {
    #                 '$inc': {'balance': -return_coin},
    #                 '$set': {'fruit': ''.join(fruit)}
    #             })
    #         self._reply_owner(update, "load done")

####################################################################################

def main(bot_profile="bot_shadow.json"):

    bot = CDInfoBot(bot_profile)                
    bot.run()

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        main()
    else:
        main(sys.argv[1])