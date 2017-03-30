'''
Author: Yu Lou(louyu27@gmail.com)

Server side program for the Werewolf game, running on Python 3.
'''
import socket
import time
import random
import struct

import audio
from audio import play_sound
from log import log
from charactor import *
import wechat

audio.audioPath = '/home/louyu/program/werewolf/audio/'

test = True

class WerewolfExploded(Exception):
    def __init__(self, player):
        self.player = player

class GameController:
    def __init__(self):
        self.have_mayor = False

    def start_game(self):
        # List of possible identities
        if test:
            self.identity = [Werewolf(self)]#[Villager(), Witch(), Werewolf()]
        else:
            self.identity = [Villager(self), Villager(self), Villager(self),\
                Witch(self), Seer(self), Savior(self),\
                Werewolf(self), Werewolf(self), Werewolf(self)]

        # Shuffle identities
        random.shuffle(self.identity)

        # Initialize player list
        self.players = [Villager(self)] + [None]*len(self.identity)
        self.players[0].died = True # Player 0 is just a placeholder
        self.players[0].player_id = 0

        # Wait for players to join the game
        while True:
            print('请按回车键开始游戏')
            input()

            can_proceed = True
            for (i, player) in enumerate(self.players[1:]):
                if player == None:
                    print('缺少%d号玩家' % (i+1))
                    can_proceed = False

            if can_proceed:
                break

        # Start the game
        play_sound('游戏开始')
        self.mainLoop()

    def mainLoop(self):
        nRound = 0
        seer, savior, witch, self.werewolves = None, None, None, []
        
        for player in self.players[1:]:
            if isinstance(player, Seer):
                seer = player
            elif isinstance(player, Witch):
                witch = player
            elif isinstance(player, Savior):
                savior = player
            elif isinstance(player, WerewolfLeader):
                self.werewolves.insert(0, player) # Insert the leader to the front
            elif isinstance(player, Werewolf):
                self.werewolves.append(player)
        
        self.killed_players = []
        # Main loop
        while True:
            nRound += 1

            # Night
            self.broadcast('-----第%d天晚上-----' % nRound)
            print(log('-----第%d天晚上-----' % nRound))

            self.broadcast('天黑请闭眼')
            play_sound('天黑请闭眼')

            self.broadcast('')
            
            self.move_for(savior)
                
            for werewolf in self.werewolves:
                if not werewolf.died:
                    self.move_for(werewolf)
                    break # Only one werewolf needs to make a choice
            
            self.move_for(witch)
            
            if witch == None:
                self.is_game_ended()
            
            self.move_for(seer)
            
            # Day
            self.broadcast('-----第%d天-----' % nRound)
            print(log('-----第%d天-----' % nRound))

            self.broadcast('天亮啦')
            play_sound('天亮了')
            
            # Vote for Mayor
            if nRound == 1:
                self.vote_for_mayor()
            
            # Show the result of last night
            self.killed_players = [player for player in self.killed_players if player.died]
            random.shuffle(self.killed_players)

            if self.killed_players:
                for player in self.killed_players:
                    self.broadcast('昨天晚上，%s 死了' % player.desc())
            else:
                self.broadcast('昨天晚上是平安夜～')

            # After dying
            for player in self.killed_players:
                player.after_dying()

            killed_players = []
            
            # Vote for suspect
            self.vote_for_suspect()

    def vote_for_mayor(self):
        targets = self.players[1:]

        # Ask for candidates
        candidates = self.broadcast_choice('是否竞选警长', '%s 竞选警长', targets = targets)

        self.broadcast('%s 竞选警长' % self.player_list_to_str(candidates))

        # Decide who can vote
        can_vote_players = [player for player in targets \
            if player not in candidates]

        # Decide speech order
        self.decide_speech_order(candidates)

        # Ask candidates whether they want to quite
        self.broadcast('正在等待候选人选择是否退水')
        quited_player = self.broadcast_choice('是否退水', '%s 退水', targets = candidates)

        for player in quited_player:
            candidates.remove(player)

        self.broadcast('%s 退水' % self.player_list_to_str(quited_player))
        self.broadcast('%s 继续竞选警长' % self.player_list_to_str(candidates))

        # Check for special situations
        if not candidates:
            return

        if len(candidates) == 1:
            mayor = candidates[0]

        # Vote
        else:
            self.broadcast('等待玩家投票')
            mayor = self.vote(candidates, '请输入你要选为警长的玩家编号', targets = can_vote_players)
        
        # Assign Mayor
        mayor.is_mayor = True
        self.have_mayor = True
        self.broadcast('%s 当选警长' % mayor.desc())

    def vote_for_suspect(self):
        targets = self.survived_players()

        # Decide speech order
        if self.have_mayor:
            self.broadcast('请警长选择发言顺序')
        else:
            self.decide_speech_order(candidates = targets)

        # Vote for suspect
        try:
            suspect = self.vote(targets, '请输入你要投出的玩家编号，狼人用0号表示爆炸', min_id = 0, targets = targets)
        
        # If a werewolf explods
        except WerewolfExploded as e:
            werewolf = e.player

            werewolf.die()
            self.broadcast('%s 爆炸' % werewolf.desc())
            werewolf.after_dying()

            werewolf.after_exploded()
        
        # Vote out the suspect
        else:
            suspect.die()
            suspect.after_dying()
            self.broadcast('%s 被投出' % suspect.desc())

        self.is_game_ended()

        # Give players some time to view the result
        self.broadcast('查看结果后，回复任意内容以继续游戏', targets = targets)
        for player in targets:
            player.get_input('')

    def decide_speech_order(self, candidates):
        first_player = random.choice(candidates)
        direction = random.choice(['顺时针', '逆时针'])
        self.broadcast('从 %s %s发言' % (first_player.desc(), direction))

    def broadcast_choice(self, message, accept_message, targets = None):
        # Broadcast message
        self.broadcast(message + '(y/n)', targets = targets)

        # Collect reply
        accepted_players = []
        for player in targets:
            if player.decide():
                accepted_players.append(player)
                print(log(accept_message % player.desc()))

        return accepted_players

    def vote(self, candidates, message, min_id = 1, targets = None):
        while True:
            vote_result = self.get_vote_result(candidates, message, min_id, targets = targets)
            self.show_vote_result(vote_result)
            
            # Check if two people get equal votes
            if vote_result[0][2] == vote_result[1][2]:
                self.broadcast('票数相同，重新投票')
                continue
            else:
                break

        return vote_result[0][0]

    def get_vote_result(self, candidates, message, min_id = 1, targets = None):
        self.broadcast(message, targets = targets)

        voted_for = [list() for i in range(len(self.players) + 1)]
        vote_count = [0.0]*(len(self.players) + 1)

        # Ask for vote
        for player in targets:
            while True:
                voted_id = player.select_player(min_id = min_id, candidates = candidates)

                # Vote for number 0 means explode
                if voted_id == 0:
                    if player.good:
                        player.message('你不能爆炸')
                        continue
                    else:
                        raise WerewolfExploded(player)
                break

            # Count votes
            voted_for[voted_id].append(player)

            if player.is_mayor:
                vote_count[voted_id] += 1.5
            else:
                vote_count[voted_id] += 1

        # Sort votes
        vote_result = [(candidate, voted_for[candidate.player_id], vote_count[candidate.player_id]) \
            for candidate in candidates]
        vote_result.sort(key = lambda x: x[2])

        return vote_result

    def show_vote_result(self, vote_results, split = ', '):
        for vote_result in vote_results:
            # Unpack data
            player = vote_result[0]
            voted_by = vote_result[1]
            vote_count = vote_result[2]

            # Get string representation of voted_by
            str_voted_by = self.player_list_to_str(voted_by)

            # Broadcast the message
            self.broadcast('%s 获得 %f 票（%s）' % (player.desc(), vote_count, str_voted_by))

    def survived_players(self):
        return [player for player in self.players[1:] if not player.died]

    def wait_random_time(self):
        time.sleep(random.random()*4+4)

    def player_list_to_str(self, players, split = ','):
        result = ''

        if players == 0:
            result = '没有人'

        for (i, player) in enumerate(players):
            if i != 0:
                result += split
            result += player.desc()

        return result

    # Check the end of game
    def is_game_ended(self):
        # Count players
        villager_count = 0
        god_count = 0
        werewolf_count = 0

        for player in self.players[1:]:
            if not player.died:
                if isinstance(player, Villager):
                    villager_count += 1
                elif player.__class__.good:
                    god_count += 1
                else:
                    werewolf_count += 1
        
        # Check if the game ends
        if villager_count == 0:
            self.broadcast('刀民成功，狼人胜利！')
            play_sound('刀民成功')
        elif god_count == 0:
            self.broadcast('刀神成功，狼人胜利！')
            play_sound('刀神成功')
        elif werewolf_count == 0:
            self.broadcast('逐狼成功，平民胜利！')
            play_sound('逐狼成功')
        else:
            return

        # End of game
        print(log('游戏结束'))
        exit()

    def move_for(self, charactor):
        if charactor == None:
            return

        charactor.open_eyes()

        if not charactor.died or charactor in self.killed_players:
            charactor.move()
        else:
            # Won't let the player close eyes immediately even if he/she died.
            time.sleep(random.random()*4+4) 

        charactor.close_eyes()

    def broadcast(self, message, targets = None):
        # Default target
        if targets == None:
            targets = self.players[1:]

        # Broadcast the message
        for player in targets:
            player.message(message)

    def broadcast_to_wolves(self, message):
        self.broadcast('狼人：' + message, targets = self.werewolves)

controller = GameController()
wechat.game_controller = controller

controller.start_game()