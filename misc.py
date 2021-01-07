#!/usr/bin/env python
# -*- coding: utf-8 -*-

def parse_token(token_file):
    with open(token_file, 'r') as f:
        for line in f:
            if line:
                return line
    return ''

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
        return 'someone'

def parse_id(id_file):
    with open(id_file, 'r') as f:
        for line in f:
            if line:
                return int(line)
    return 0