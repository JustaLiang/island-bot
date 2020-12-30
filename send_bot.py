#!/usr/bin/env python
# -*- coding: utf-8 -*-

import telebot

TOKEN = '1415640092:AAGjpSpqw0wLFUiy-mw4Mi9IoPNelsxV8YQ'
MY_ID = 1496518066
GP_ID = -400364252
tb = telebot.TeleBot(TOKEN)	#create a new Telegram Bot object

# sendMessage
while True:
	try:
		msg = input("> ")
		tb.send_message(GP_ID, msg)

	except KeyboardInterrupt:
		print("end bot")
		break