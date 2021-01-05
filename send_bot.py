#!/usr/bin/env python
# -*- coding: utf-8 -*-

import telebot
from parse_token import parse_token

def main():
	
	TOKEN = parse_token('token_CD_parse_bot')

	if not TOKEN:
		return

	MY_ID = 1496518066
	GP_ID = -1001182325701
	tb = telebot.TeleBot(TOKEN)	#create a new Telegram Bot object

	# sendMessage
	while True:
		try:
			msg = input("> ")
			tb.send_message(GP_ID, msg)

		except KeyboardInterrupt:
			print("\n[END]")
			return


if __name__ == '__main__':
	main()