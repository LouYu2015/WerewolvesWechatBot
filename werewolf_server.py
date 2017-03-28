'''
Author: Yu Lou(louyu27@gmail.com)

Server side program for the Werewolf game, running on Python 3.
'''
import socket
import threading
import time
import random
import struct
import queue

import itchat

from characters import *

import audio
from audio import playSound

CLR_STRING = '\n'*25 + '清屏'

audio.audioPath = '/home/louyu/program/werewolf/audio/'

test = True

def main():
    global players, identity

    # List of possible identities
    if test:
        identity = [Werewolf()]#[Villager(), Witch(), Werewolf()]
    else:
        identity = [Villager(), Villager(), Villager(),\
            Witch(), Seer(), Savior(),\
            Werewolf(), Werewolf(), Werewolf()]# Identities for each player

    # Shuffle identities
    random.seed(time.time())
    random.shuffle(identity)

    # Initialize player list
    players = [None]*(len(identity) + 1) # No.0 Player won't be used

    # Start itchat
    itchat.auto_login()
    threading.Thread(target = itchat.run).start()

    # Wait for players to enter the game
    while True:
        print('请按回车键开始游戏')
        input()

        can_proceed = True
        for (i, player) in enumerate(players[1:]):
            if player == None:
                print('缺少%d号玩家' % (i+1))
                can_proceed = False

        if can_proceed:
            break

    # Start the game
    playSound('游戏开始')
    mainLoop()

username_to_user = {} # Map Wechat user name to WechatUser object

class WechatUser:
    def __init__(self, userName):
        self.msg_queue = queue.Queue()
        self.userName = userName

        username_to_user[userName] = self

    def gotMessage(self, message):
        self.msg_queue.put(message)

    def sendMessage(self, message):
        itchat.send(message, toUserName = self.userName)

    def receiveMessage(self):
        return self.msg_queue.get() # Will block when there's no new message

    def getInput(self, message):
        self.sendMessage(message)
        return self.receiveMessage()

# Accept a new message from players
@itchat.msg_register(itchat.content.TEXT) # Register as a listener
def listenText(message):
    username = message['User']['UserName'] # User name of the Wechat user
    text = message['Text'] # Content of the message

    # Get remark name
    try:
        remarkname = message['User']['RemarkName']
    except KeyError:
        remarkname = None

    # If a user wants to enter the game
    if '进入游戏' in text:
        user = WechatUser(username)
        print(log('%s 作为 %s 进入了游戏' % (username, remarkname)))

        threading.Thread(target = handleRequest, args = (user,remarkname)).start()
    
    # If it's other message
    else:
        try:
            username_to_user[username].gotMessage(text)
        except KeyError:
            print(log('无效的消息:%s %s\n%s' % (remarkname, username, text)))

def handleRequest(user, remarkname):
    if not remarkname:
        remarkname = user.getInput('您没有备注名，请输入你的名字')
        print('%s 更名为 %s' % (user.userName, remarkname))

    # Ask for the player's ID
    while True:
        try:
            player_id = int(user.getInput('请输入你的编号'))
        except ValueError:
            user.sendMessage('这不是数字')
            continue
            
        if not(player_id >= 1 and player_id < len(players)):
            user.sendMessage('超出编号范围')
            continue

        if players[player_id]:
            user.sendMessage('该编号已被占用')
            continue

        break
        
    players[player_id] = identity.pop() # Assign an identity
    
    player = players[player_id]
    player.player_id = player_id
    player.user = user
    player.name = remarkname

    player.welcome()
    
    print(log('%s已经上线' % players[player_id].num()))

def mainLoop():
    global players, lastKilled, nRound

    nRound = 0
    seer, savior, witch, werewolves = None, None, None, []
    
    for player in players[1:]:
        if isinstance(player, Seer):
            seer = player
        elif isinstance(player, Witch):
            witch = player
        elif isinstance(player, Savior):
            savior = player
        elif isinstance(player, WerewolfLeader):
            werewolves.insert(0, player) # Insert the leader to the front
        elif isinstance(player, Werewolf):
            werewolves.append(player)
    
    # Main loop
    while True:
        lastKilled = []
        nRound += 1

        broadcast('-----第%d天晚上-----' % (nRound-1))
        print(log('-----第%d天晚上-----' % (nRound-1)))
        broadcast('天黑请闭眼')
        playSound('天黑请闭眼')

        broadcast(CLR_STRING)
        
        moveFor(savior)
            
        for werewolf in werewolves:
            if not werewolf.died:
                moveFor(werewolf)
                break # Only one werewolf needs to make a choice
        
        moveFor(witch)
        
        if witch == None:
            isGameEnded()
        
        moveFor(seer)
        
        broadcast('-----第%d天-----' % nRound)
        print(log('-----第%d天-----' % nRound))
        broadcast('天亮啦')
        playSound('天亮了')
        
        agent = players[1]
        broadcast('%s 将记录白天的情况' % agent.num())
        
        if nRound == 1:
            agent.inputFrom('警长竞选结束时，请按回车：')
        
        anyoneDied = False
        random.shuffle(lastKilled)
        for player in lastKilled:
            if player.died:
                broadcast('昨天晚上，%s死了' % player.num())
                anyoneDied = True
        if not anyoneDied:
            broadcast('昨天晚上是平安夜～')

        for player in lastKilled:
            if player.died:
                player.afterDying()
        
        exploded = False
        while True:
            if not agent.selectFrom('是否有狼人爆炸'):
                broadcast('操作员选择无人爆炸')
                break
            explodedMan = agent.selectPlayer('输入该狼人的编号')
            if not agent.selectFrom('是否确认对方的编号是 %d' % explodedMan):
                continue
            explodedMan = players[explodedMan]
            if explodedMan.died:
                agent.message('此玩家已经死亡，不能爆炸')
                continue
            if not isinstance(explodedMan, Werewolf):
                broadcast('操作员选择的不是狼！')
                continue
            else:
                broadcast('操作员选择%s爆炸' % explodedMan.num())
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
            broadcast('操作员选择了平票')
            continue
        toKill = players[toKill]
        broadcast('操作员选择投死%s' % toKill.num())
        print(log('%s被处死' % toKill.description()))
        toKill.die()
        toKill.afterDying()

def moveFor(char):
    if char == None:
        return
    if not char.died or char in lastKilled:
        char.openEyes()
        char.move()
        char.closeEyes()
    else:
        time.sleep(random.random()*4+4) # Won't let the player close eyes immediately even if he/she died.

# Add time to message
def log(string):
    return '[%s]%s' % (time.strftime('%H:%M:%S'), string)

# Broadcast
def broadcast(string):
    for player in players[1:]:
        player.message(string)

def broadcastToWolves(string):
    for wolf in werewolves:
        wolf.message('狼人：' + string)

# Check the end of game
def isGameEnded():
    villagerCount = 0
    godCount = 0
    werewolfCount = 0

    for player in players[1:]:
        if not player.died:
            if isinstance(player, Villager):
                villagerCount += 1
            elif player.good:
                godCount += 1
            else:
                werewolfCount += 1
    
    if villagerCount == 0:
        broadcast('刀民成功，狼人胜利！')
        playSound('刀民成功')
    elif godCount == 0:
        broadcast('刀神成功，狼人胜利！')
        playSound('刀神成功')
    elif werewolfCount == 0:
        broadcast('逐狼成功，平民胜利！')
        playSound('逐狼成功')
    else:
        return

    print(log('游戏结束'))
    exit()

class Character:
    def __init__(self):
        self.sock = None # Socket connection
        self.player_id = None # Order player_id of the player
        self.died = False # Is player died
        self.protected = False # Is player protected by Savior
        self.good = None # Is player good or bad
        self.name = '' # Player's name
        self.identity = '' # Player's character name
    
    def welcome(self):# Tell the player his/her identity
        self.message('你是%s' % self.description())
    
    def message(self, message): # Send message to player
        self.user.sendMessage(message)

    def inputFrom(self, message):# Get input from player
        return self.user.getInput(message).strip()
    
    def selectFrom(self, string):# Let the player select yes/no
        while True:
            answer = self.inputFrom(string + '(y/n)：')
            if answer == 'Y' or answer == 'y':
                return True
            elif answer == 'N' or answer == 'n':
                return False
            self.message('输入错误，请输入Y/y(yes)或者N/n(no)')
    
    def selectPlayer(self, string, minNumber = 1):# Let the player select a player
        while True:
            try:
                answer = int(self.inputFrom(string + '：'))
            except ValueError:
                self.message('这不是数字')
                continue
                
            if not(answer >= minNumber and answer < len(players)):
                self.message('超出编号范围')
                continue
            return answer
    
    def kill(self):# Try to kill the player
        lastKilled.append(self)
        if not self.protected:
            self.die(True)
        return self.died
    
    def die(self, killedByWolf = False):# Make the player died
        self.died = True
        if not killedByWolf:
            lastKilled.append(self)
            isGameEnded()
    
    def afterDying(self):
        pass
    
    def num(self):
        return '%d号%s' % (self.player_id, self.name)
    
    def description(self):
        return '%d号%s%s' % (self.player_id, self.identity, self.name)
    
    def openEyes(self):
        playSound('%s请睁眼' % self.identity)
    
    def closeEyes(self):
        playSound('%s请闭眼' % self.identity)
        self.message(CLR_STRING)
    
class Witch(Character):
    def __init__(self):
        super().__init__()
        self.identity = '女巫'
        self.good = True
        self.usedPoison = False
        self.usedMedicine = False
    
    def move(self):
        if self.usedMedicine:
            self.message('你用过解药了')
        else:
            try:
                diedMan = lastKilled[-1]
            except IndexError:
                self.message('刚才是空刀')
            else:
                self.message('刚才%s被杀了' % diedMan.num())

                if (nRound >= 2 and diedMan is self):
                    self.message('第二回合起你不能自救')
                elif not self.selectFrom('是否救人'):
                    print(log('%s没有救人' % self.description()))
                else:
                    print(log('%s救了%s' % (self.description(), diedMan.description())))
                    self.usedMedicine = True
                    diedMan.died = False
                    
                    if diedMan.protected:
                        print(log('同守同救！'))
                        diedMan.died = True
        isGameEnded()
            
        if self.usedPoison:
            time.sleep(random.random()*4+4)# Won't let the player close eyes immediately
            self.message('你用过毒药了')
        else:
            if self.selectFrom('是否使用毒药'):
                manToKill = self.selectPlayer('输入要毒死的玩家,0表示取消', minNumber = 0)
                if manToKill != 0:
                    manToKill = players[manToKill]
                    print(log('%s毒死了%s' % (self.description(), manToKill.description())))
                    manToKill.die()
                    manToKill.canUseGun = False
                    self.usedPoison = True

class Savior(Character):
    def __init__(self):
        super().__init__()
        self.identity = '守卫'
        self.good = True
        self.lastProtected = players[0]
    
    def move(self):
        while True:
            protectedMan = self.selectPlayer('输入要守护的人,0表示空守', minNumber = 0)
            protectedMan = players[protectedMan]
            
            if protectedMan.player_id != 0 and protectedMan is self.lastProtected:
                self.message('连续的回合里不能守护同一个人')
                continue
            break
        self.lastProtected.protected = False
        protectedMan.protected = True
        print(log('%s守护了%s' % (self.description(), protectedMan.description())))
        
        self.lastProtected = protectedMan

class Seer(Character):
    def __init__(self):
        super().__init__()
        self.identity = '预言家'
        self.good = True
    
    def move(self):
        while True:
            watchedMan = self.selectPlayer('选择你要预言的人')
            watchedMan = players[watchedMan]
            if watchedMan.died and watchedMan not in lastKilled:
                self.message('你不能验死人')
                continue
            break
        if watchedMan.good:
            self.message('%s是好人' % watchedMan.num())
            print(log('%s发现%s是金水' % (self.description(), watchedMan.description())))
        else:
            self.message('%s是坏人' % watchedMan.num())
            print(log('%s发现%s是查杀' % (self.description(), watchedMan.description())))
            
class Hunter(Character):
    def __init__(self):
        super().__init__()
        self.identity = '猎人'
        self.good = True
        self.canUseGun = True
    
    def afterDying(self):
        if not self.canUseGun:
            self.message('你是被女巫毒死的，不能放枪')
            return
        
        player = self.selectPlayer('输入你要枪杀的玩家，0表示不放枪', minNumber = 0)
        
        if player == 0:
            print(log('猎人没有放枪'))
            return
        
        player = players[player]
        
        broadcast('%s枪杀了%s' % (self.description(), player.num()))
        print(log('%s枪杀了%s' % (self.description(), player.description())))
        player.die()

class Werewolf(Character):
    def __init__(self):
        super().__init__()
        self.identity = '狼人'
        self.good = False
    
    def move(self):
        broadcastToWolves('由%s代表狼人进行操作' % self.description())
        killedMan = self.selectPlayer('输入你要杀的玩家，0表示空刀', minNumber = 0)
        if killedMan == 0:
            broadcastToWolves('狼人选择空刀')
            print(log('狼人空刀'))
            return
        killedMan = players[killedMan]
        killedMan.kill()
        broadcastToWolves('狼人选择刀%s' % killedMan.num())
        print(log('狼人刀%s' % killedMan.description()))
    
    def afterExploded(self):
        self.message('你不能带人')

class WerewolfLeader(Werewolf):
    def __init__(self):
        super().__init__()
        self.identity = '狼王'
    
    def afterExploded(self):
        if self.selectFrom('是否要带人'):
            killedMan = self.selectPlayer('输入你要带走的人')
            killedMan = players[killedMan]
            killedMan.die()
            broadcast('%s带走了%s' % (self.description(), killedMan.num()))
            print(log('%s带走了%s' % (self.description(), killedMan.description())))
        
    def openEyes(self):
        playSound('狼人请睁眼')
    
    def closeEyes(self):
        playSound('狼人请闭眼')
        
class Villager(Character):
    def __init__(self):
        super().__init__()
        self.identity = '村民'
        self.good = True

main()
