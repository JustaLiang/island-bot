#!/usr/bin/env python
# -*- coding: utf-8 -*-

def message_info(message):
    '''
    Return
        c_id, u_id, u_name
    '''
    c_id = message.chat.id
    u_id = message.from_user.id
    m_id = message.message_id
    u_name = message.from_user.full_name
    return c_id, u_id, u_name, m_id

def players_want2play_str(players):
    players_y = []
    players_n = []
    for u_id, player in players.items():
        if player.play == False:
            players_n.append(player.name)
        else:
            players_y.append(player.name)

    players_y_str = ', '.join(players_y) if len(players_y) else '暫無'
    players_n_str = ', '.join(players_n) if len(players_n) else '暫無'

    return f'要玩: {players_y_str}\n不要: {players_n_str}'
