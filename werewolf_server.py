'''
Author: Yu Lou(louyu27@gmail.com)

Server side program for the Werewolf game, running on Python 3.
'''
import socket
import time
import random
import struct

import audio
from audio import playSound
from log import log
from charactor import *
import wechat

audio.audioPath = '/home/louyu/program/werewolf/audio/'

test = True

class WerewolfExploded(Exception):
    def __init__(self, player):
        self.player = player

class gameController:
    def startGame(self):
        # List of possible identities
        if test:
            self.identity = [Werewolf(self)]#[Villager(), Witch(), Werewolf()]
        else:
            self.identity = [Villager(self), Villager(self), Villager(self),\
                Witch(self), Seer(self), Savior(self),\
                Werewolf(self), Werewolf(self), Werewolf(self)]# Identities for each player

        # Shuffle identities
        random.seed(time.time())
        random.shuffle(self.identity)

        # Initialize player list
        self.players = [Villager(self)] + [None]*len(self.identity) # No.0 Player won't be used
        self.players[0].died = True # Player 0 is just a placeholder
        self.players[0].player_id = 0

        # Wait for players to enter the game
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
        playSound('游戏开始')
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
        
        self.lastKilled = []
        # Main loop
        while True:
            nRound += 1

            # Night
            self.broadcast('-----第%d天晚上-----' % (nRound-1))
            print(log('-----第%d天晚上-----' % (nRound-1)))
            self.broadcast('天黑请闭眼')
            playSound('天黑请闭眼')

            self.broadcast('')
            
            self.moveFor(savior)
                
            for werewolf in self.werewolves:
                if not werewolf.died:
                    self.moveFor(werewolf)
                    break # Only one werewolf needs to make a choice
            
            self.moveFor(witch)
            
            if witch == None:
                self.isGameEnded()
            
            self.moveFor(seer)
            
            # Day
            self.broadcast('-----第%d天-----' % nRound)
            print(log('-----第%d天-----' % nRound))
            self.broadcast('天亮啦')
            playSound('天亮了')
            
            # Vote for Mayor
            if nRound == 1:
                self.voteForMayor()
            
            # Show the result of last night
            self.lastKilled = [player for player in self.lastKilled if player.died]
            random.shuffle(self.lastKilled)
            if self.lastKilled:
                for player in self.lastKilled:
                    self.broadcast('昨天晚上，%s死了' % player.desc())
            else:
                self.broadcast('昨天晚上是平安夜～')

            lastKilled = []

            # After dying
            for player in self.lastKilled:
                player.afterDying()
            
            # Vote for suspect
            self.voteForSuspect()

    def voteForMayor(self):
        targets = self.players[1:]

        # Ask for candidates
        candidates = self.broadcastChoice('是否竞选警长', '%s 竞选警长', targets = targets)

        # Decide who can vote
        can_vote_player = [player for player in targets \
            if player not in candidates]

        # Decide speech order
        self.decideSpeechOrder(candidates)

        # Ask candidates whether they want to quite
        self.broadcast('正在等待候选人选择是否退水')
        quited_player = self.broadcastChoice('是否退水', '%s 退水', targets = candidates)

        for player in quited_player:
            candidates.remove(player)

        # Check for special situations
        if not candidates:
            self.broadcast('没有人竞选警长')
            return

        if len(candidates) == 1:
            mayer = candidates[0]
            self.broadcast('%s 成为唯一候选人' % mayer.desc())

        # Vote
        else:
            self.broadcast('等待玩家投票')
            mayer = self.vote(candidates, '请输入你要选为警长的玩家编号', targets = can_vote_player)
        
        # Assign Mayer
        mayer.is_mayer = True
        self.broadcast('%s 当选警长' % mayer.desc())

    def voteForSuspect(self):
        targets = self.survivedPlayers()

        # Decide speech order
        self.decideSpeechOrder(targets)

        # Vote for suspect
        try:
            suspect = self.vote(targets, '请输入你要投出的玩家编号，狼人用0号表示爆炸', min_id = 0, targets = targets)
        
        # If a werewolf explods
        except WerewolfExploded as e:
            werewolf = e.player
            werewolf.die()

            self.broadcast('%s 爆炸' % werewolf.desc())
            werewolf.afterDying()
            werewolf.afterExploded()
        
        # Vote out the suspect
        else:
            suspect.die()
            suspect.afterDying()
            self.isGameEnded()
            self.broadcast('%s 被投出' % suspect.desc())

        # Give players some time to view the result
        self.broadcast('查看结果后，回复任意内容以继续游戏', targets = targets)
        for player in targets:
            player.inputFrom('')

    def decideSpeechOrder(self, candidates):
        first_player = random.choice(candidates)
        direction = random.choice(['顺时针', '逆时针'])
        self.broadcast('从 %s %s发言' % (first_player.desc(), direction))

    def broadcastChoice(self, message, accept_message, targets = None):
        # Broadcast message
        self.broadcast(message + '(y/n)', targets = targets)

        # Collect reply
        accepted_players = []
        for player in targets:
            if player.selectFrom():
                accepted_players.append(player)

                self.broadcast(accept_message % player.desc())
                print(log(accept_message % player.desc()))

        return accepted_players

    def vote(self, candidates, message, targets = None):
        while True:
            vote_result = self.getVoteResult(candidates, message, targets = targets)
            self.showVoteResult(vote_result)
            
            # Check if two people get equal votes
            if vote_result[0][2] == vote_result[1][2]:
                self.broadcast('票数相同，重新投票')
                continue
            else:
                break

        return vote_result[0][0]

    def getVoteResult(self, candidates, message, min_id = 1, targets = None):
        self.broadcast(message, targets = targets)

        voted_for = [list() for i in range(len(self.players) + 1)]
        vote_count = [0.0]*(len(self.players) + 1)

        # Ask for vote
        for player in targets:
            while True:
                voted_id = player.selectPlayer(min_id = min_id, candidates = candidates)

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

    def showVoteResult(self, vote_results, split = ', '):
        for vote_result in vote_results:
            # Unpack data
            player = vote_result[0]
            voted_by = vote_result[1]
            vote_count = vote_result[2]

            # Get string representation of voted_by
            str_voted_by = ''
            if vote_count == 0:
                str_voted_by = '没有人'
            else:
                for (i, voted) in enumerate(voted_by):
                    if i != 0:
                        str_voted_by += split
                    str_voted_by += voted.desc()

            # Broadcast the message
            self.broadcast('%s 获得 %f 票（%s）' % (player.desc(), vote_count, str_voted_by))

    def survivedPlayers(self):
        return [player for player in self.players[1:] if not player.died]

    # Check the end of game
    def isGameEnded(self):
        # Count players
        villagerCount = 0
        godCount = 0
        werewolfCount = 0

        for player in self.players[1:]:
            if not player.died:
                if isinstance(player, Villager):
                    villagerCount += 1
                elif player.__class__.good:
                    godCount += 1
                else:
                    werewolfCount += 1
        
        # Check if the game ends
        if villagerCount == 0:
            self.broadcast('刀民成功，狼人胜利！')
            playSound('刀民成功')
        elif godCount == 0:
            self.broadcast('刀神成功，狼人胜利！')
            playSound('刀神成功')
        elif werewolfCount == 0:
            self.broadcast('逐狼成功，平民胜利！')
            playSound('逐狼成功')
        else:
            return

        # End of game
        print(log('游戏结束'))
        exit()

    def moveFor(self, char):
        if char == None:
            return

        char.openEyes()

        if not char.died or char in self.lastKilled:
            char.move()
        else:
            # Won't let the player close eyes immediately even if he/she died.
            time.sleep(random.random()*4+4) 

        char.closeEyes()

    def broadcast(self, message, targets = None):
        # Default target
        if targets == None:
            targets = self.players[1:]

        # Broadcast the message
        for player in targets:
            player.message(message)

    def broadcastToWolves(self, message):
        self.broadcast('狼人：' + message, targets = self.werewolves)

controller = gameController()
wechat.game_controller = controller

controller.startGame()