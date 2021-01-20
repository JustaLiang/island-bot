#!/usr/bin/env python
# -*- coding: utf-8 -*-

import telebot
from parse import parse_token, parse_id

def main():
	
	TOKEN = parse_token('token_CD_parse_bot')

	if not TOKEN:
		return

	GP_ID = parse_id("id_melon_group")
	if GP_ID == 0:
		print("id file not found")
		return
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