#!/usr/bin/env python
# -*- coding: utf-8 -*-

def parse_token(token_file):
    with open(token_file, 'r') as f:
        for line in f:
            if line:
                return line
    return ''