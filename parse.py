#!/usr/bin/env python
# -*- coding: utf-8 -*-

def parse_token(token_file):
    try:
        with open(token_file, 'r') as f:
            for line in f:
                if line:
                    return line
    except:
        return ''

def parse_id(id_file):
    try:
        with open(id_file, 'r') as f:
            for line in f:
                if line:
                    return int(line)
    except:
        return 0