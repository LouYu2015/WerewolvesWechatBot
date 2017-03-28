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

CLR_STRING = '\n'*25 + '清屏'

audio.audioPath = '/home/louyu/program/werewolf/audio/'

test = True

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
        self.players = [None]*(len(self.identity) + 1) # No.0 Player won't be used

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
        
        # Main loop
        while True:
            self.lastKilled = []
            nRound += 1

            self.broadcast('-----第%d天晚上-----' % (nRound-1))
            print(log('-----第%d天晚上-----' % (nRound-1)))
            self.broadcast('天黑请闭眼')
            playSound('天黑请闭眼')

            self.broadcast(CLR_STRING)
            
            self.moveFor(savior)
                
            for werewolf in self.werewolves:
                if not werewolf.died:
                    self.moveFor(werewolf)
                    break # Only one werewolf needs to make a choice
            
            self.moveFor(witch)
            
            if witch == None:
                self.isGameEnded()
            
            self.moveFor(seer)
            
            self.broadcast('-----第%d天-----' % nRound)
            print(log('-----第%d天-----' % nRound))
            self.broadcast('天亮啦')
            playSound('天亮了')
            
            agent = self.players[1]
            self.broadcast('%s 将记录白天的情况' % agent.num())
            
            if nRound == 1:
                agent.inputFrom('警长竞选结束时，请按回车：')
            
            anyoneDied = False
            random.shuffle(self.lastKilled)
            for player in self.lastKilled:
                if player.died:
                    self.broadcast('昨天晚上，%s死了' % player.num())
                    anyoneDied = True
            if not anyoneDied:
                self.broadcast('昨天晚上是平安夜～')

            for player in self.lastKilled:
                if player.died:
                    player.afterDying()
            
            exploded = False
            while True:
                if not agent.selectFrom('是否有狼人爆炸'):
                    self.broadcast('操作员选择无人爆炸')
                    break
                explodedMan = agent.selectPlayer('输入该狼人的编号')
                if not agent.selectFrom('是否确认对方的编号是 %d' % explodedMan):
                    continue
                explodedMan = self.players[explodedMan]
                if explodedMan.died:
                    agent.message('此玩家已经死亡，不能爆炸')
                    continue
                if not isinstance(explodedMan, Werewolf):
                    self.broadcast('操作员选择的不是狼！')
                    continue
                else:
                    self.broadcast('操作员选择%s爆炸' % explodedMan.num())
                    print(log('%s爆炸' % explodedMan.description()))
                    explodedMan.die()
                    explodedMan.afterExploded()
                    exploded = True
                    break
            
            if exploded:
                continue
            
            toKill = agent.selectPlayer('选择投死的玩家编号，0为平票', minNumber = 0)
            if toKill == 0:
                print(log('平票，没有人被处死'))
                self.broadcast('操作员选择了平票')
                continue
            toKill = self.players[toKill]
            self.broadcast('操作员选择投死%s' % toKill.num())
            print(log('%s被处死' % toKill.description()))
            toKill.die()
            toKill.afterDying()

    # Check the end of game
    def isGameEnded(self):
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

        print(log('游戏结束'))
        exit()

    def moveFor(self, char):
        if char == None:
            return

        if not char.died or char in self.lastKilled:
            char.openEyes()
            char.move()
            char.closeEyes()
        else:
            time.sleep(random.random()*4+4) # Won't let the player close eyes immediately even if he/she died.

    def broadcast(self, string):
        for player in self.players[1:]:
            player.message(string)

    def broadcastToWolves(self, string):
        for wolf in self.werewolves:
            wolf.message('狼人：' + string)

controller = gameController()
wechat.game_controller = controller

controller.startGame()