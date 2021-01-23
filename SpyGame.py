#!/usr/bin/env python

from enum import Enum
import numpy as np
import copy
import util

class Identity(Enum):
    NEUTRAL = 0
    CIVILIAN = 1
    SPY = -1

    def __str__(self):
        if self.value == 0:
            return '白板'
        elif self.value == 1:
            return '平民'
        elif self.value == -1:
            return '臥底'
        else:
            raise

class State(Enum):
    IDLE = 0
    REGISTER = 1
    CLUE = 2
    DISCUSS = 3
    POLL = 4
    KILL = 5
    HOST = -1

    def __str__(self):
        if self.value == 0:
            return '閒置'
        elif self.value == 1:
            return '註冊'
        elif self.value == 2:
            return '提示'
        elif self.value == 3:
            return '討論'
        elif self.value == 4:
            return '投票'
        elif self.value == 5:
            return '殺人'
        return f'{self.value}未定義'

class Player:
    def __init__(self, u_id, u_name):
        self.id = u_id
        self.name = u_name

        self.clues = []
        self.identity = Identity.CIVILIAN
        self.alive = True
        self.votes = 0
        self.voted = False

        self.play = False

    def reset(self):
        self.clues = []
        self.alive = True
        self.votes = 0
        self.voted = False

class SpyGame:

    def __init__(self, c_id, h_id, h_name):
        # Game ID, for users and hosts
        self.g_id = -1
        # Chat room ID
        self.c_id = c_id
        # Host User ID
        self.h_id = h_id
        # Host User Name
        self.h_name = h_name

        self.num_identity_dict = {
            1: {Identity.NEUTRAL: 0, Identity.CIVILIAN: 1, Identity.SPY: 0},
            2: {Identity.NEUTRAL: 1, Identity.CIVILIAN: 1, Identity.SPY: 0},
            3: {Identity.NEUTRAL: 0, Identity.CIVILIAN: 2, Identity.SPY: 1},
            4: {Identity.NEUTRAL: 1, Identity.CIVILIAN: 2, Identity.SPY: 1},
            5: {Identity.NEUTRAL: 1, Identity.CIVILIAN: 3, Identity.SPY: 1},
            6: {Identity.NEUTRAL: 1, Identity.CIVILIAN: 4, Identity.SPY: 1},
            7: {Identity.NEUTRAL: 1, Identity.CIVILIAN: 4, Identity.SPY: 2},
        }
        self.init()

    def init(self):
        self.identity_count = {
            Identity.NEUTRAL: 0,
            Identity.CIVILIAN: 0,
            Identity.SPY: 0
        }

        self.words = {
            Identity.NEUTRAL: '(你是白板)',
            Identity.CIVILIAN: 'Orange',
            Identity.SPY: 'Apple'
        }
        self.players = {}
        self.reset()

    def reset(self):
        for u_id, player in self.players.items():
            player.reset()

        self.m_id = {}
        self.m_id['register_button'] = -1
        self.m_id['poll_button'] = -1
        self.m_id['kill_button'] = -1
        self.m_id['host_button'] = -1
        self.set_state(State.IDLE)
        self.clue_idx = 0

    def log_voted(self):
        voted = []
        not_voted = []
        for u_id, player in self.players.items():
            if player.alive and player.play:
                if player.voted is False:
                    not_voted.append(player.name)
                else:
                    voted.append(player.name)
        ret = '\n已投票：' +', '.join(voted) + '\n未投票：'+', '.join(not_voted) + '\n'
        return ret

    def log_identity_count(self):
        ret = []
        for x in self.identity_count:
            ret.append(f' {self.identity_count[x]}位{str(x)}')
        return ', '.join(ret)

    def log_players_name(self):
        ret = [ player.name for u_id, player in self.players.items() if player.play ]
        ret = ', '.join(ret)
        return f'玩家有: {ret}'

    def log_clue_history(self):
        ret = '剛剛都說了這些：'
        #for h in self.players:
        #    ret += f'\n{h[0]} 提示 {h[1]}'
        for u_id, player in self.players.items():
            if player.play:
                clues_str = [ f'({idx}) {clue}' for idx, clue in player.clues ]
                ret += f'\n{player.name}: {" ".join(clues_str)}'
        return ret

    def log_words(self):
        ret = f'{str(Identity.CIVILIAN)}: {self.words[Identity.CIVILIAN]}\n'
        ret += f'{str(Identity.SPY)}: {self.words[Identity.SPY]}'
        return ret

    def set_host(self, h_id, h_name):
        self.h_id = h_id

    def set_state(self, state):
        self.state = state

    def set_words(self, w1, w2, random):
        words = [w1, w2]
        if random:
            np.random.shuffle(words)
            self.words[Identity.CIVILIAN] = words[0]
            self.words[Identity.SPY] = words[1]
            ret_msg = f'{self.g_id}號房的平民與臥底詞彙隨機設定成{w1}或{w2}'
            return ret_msg
        else:
            self.words[Identity.CIVILIAN] = words[0]
            self.words[Identity.SPY] = words[1]
            ret_msg = f'{self.g_id}號房的平民隨機設定成{w1}且臥底詞彙設定成{w2}'
            return ret_msg

    def register(self, u_id, u_name, play=True):
        if u_id not in self.players:
            self.players[u_id] = Player(u_id, u_name)
        player = self.players[u_id]
        update = (play != player.play)
        if play:
            player.play = True
        else:
            player.play = False
        return update

    def wrong_state(self):
        return f"時候未到，現在{str(self.state)}中"

    def not_host(self):
        return f'不要亂點好嗎 只有主持人{self.h_name}能按'

    def random_set_player_identity(self):
        N = len([ player for u_id, player in self.players.items() if player.play ])
        tmp = []
        for x in [Identity.NEUTRAL, Identity.CIVILIAN, Identity.SPY]:
            self.identity_count[x] = self.num_identity_dict[N][x]
            for _ in range(self.identity_count[x]):
                tmp.append(x)

        np.random.shuffle(tmp)
        i = 0
        for _, (u_id, player) in enumerate(self.players.items()):
            if player.play:
                player.identity = tmp[i]
                i += 1

    def init_turn(self):
        self.turn_order = [ u_id for u_id, player in self.players.items() if player.alive and player.play ]
        np.random.shuffle(self.turn_order)
        self.turn_index = -1
        self.state = State.CLUE
        return f'本局順序為 {", ".join([ self.players[u_id].name for u_id in self.turn_order ])}'

    def end_turn(self):
        info_str = '大家都說完了吧'
        info_str += '\n' + self.log_clue_history()
        info_str += '\n請開始你們的內鬨'
        self.state = State.DISCUSS
        return False, info_str

    def next_player(self):
        self.turn_index += 1
        num_alive = len([ player for u_id, player in self.players.items() if player.alive and player.play ])
        if self.turn_index == num_alive:
            return self.end_turn()
        else:
            self.next_u_id = self.turn_order[self.turn_index]
            self.next_u_name = self.players[self.next_u_id].name
            return True, f'{self.next_u_name} 輪到你了 講話啊'

    def kill_player(self, u_id):
        victim_name = self.players[u_id].name

        self.players[u_id].alive = False
        victim_identity = self.players[u_id].identity
        info_str = f'{victim_name} 死了 他的身份是{str(victim_identity)}'
        self.identity_count[victim_identity] -= 1
        info_str += '\n本局還剩下：' + self.log_identity_count()
        return self.win_condition(), info_str

    def add_clue(self, u_id, clue):
        self.clue_idx += 1
        self.players[u_id].clues.append((self.clue_idx, clue))

    def win_condition(self):
        if self.identity_count[Identity.SPY] == 0:
            if self.identity_count[Identity.NEUTRAL] == 1:
                win_player = [ player.name for u_id, player in self.players.items() if player.identity == Identity.NEUTRAL and player.play]
                info_str = f'{str(Identity.NEUTRAL)} 贏了: {win_player[0]}'
                info_str += '\n' + self.log_words()
                info_str += '\n' + self.log_clue_history()
                return True, info_str
            elif self.identity_count[Identity.NEUTRAL] == 0:
                win_players = [ player.name for uid, player in self.players.items() if player.identity == Identity.CIVILIAN and player.play]
                info_str = f'{str(Identity.CIVILIAN)} 贏了: {", ".join(win_players)}'
                info_str += '\n' + self.log_words()
                info_str += '\n' + self.log_clue_history()
                return True, info_str
        elif self.identity_count[Identity.NEUTRAL] == 0:
            if self.identity_count[Identity.SPY] > self.identity_count[Identity.CIVILIAN] or self.identity_count[Identity.CIVILIAN] == 1:
                win_players = [ player.name for uid, player in self.players.items() if player.identity == Identity.SPY and player.play]
                info_str = f'{str(Identity.SPY)}贏了: {", ".join(win_players)}'
                info_str += '\n' + self.log_words()
                info_str += '\n' + self.log_clue_history()
                return True, info_str
        return False, '開始下回合'
