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

    # Initialize player list
    players = [None]

    # List of possible identities
    if test:
        identity = [Wolf()]#[Villager(), Witch(), Wolf()]
    else:
        identity = [Villager(), Villager(), Villager(),\
            Witch(), Prophet(), Guard(),\
            Wolf(), Wolf(), Wolf()]# Identities for each player

    # Shuffle identities
    random.seed(time.time())
    random.shuffle(identity)

    players += [None]*len(identity)

    itchat.auto_login()
    threading.Thread(target = itchat.run).start()

    while True:
        print('请按回车键开始游戏')
        input()
        proceed = True
        for (i, player) in enumerate(players[1:]):
            if player == None:
                print('缺少%d号玩家' % (i+1))
                proceed = False 
        if not proceed:
            continue
        break

    playSound('游戏开始')
    mainLoop()

username_to_user = {}

class WechatUser:
    def __init__(self, userName):
        self.queue = queue.Queue()
        self.newMessage = threading.Event()
        self.userName = userName

        username_to_user[userName] = self

    def sendMessage(self, message):
        itchat.send(message, toUserName = self.userName)

    def gotMessage(self, message):
        self.queue.put(message)
        self.newMessage.set()

    def getInput(self, message):
        self.sendMessage(message)
        self.newMessage.wait()
        self.newMessage.clear()
        return self.queue.get()

@itchat.msg_register(itchat.content.TEXT)
def listenText(message):
    username = message['User']['UserName']
    text = message['Text']
    try:
        remarkname = message['User']['RemarkName']
    except KeyError:
        remarkname = 'self'

    if '进入游戏' in text:
        user = WechatUser(username)
        print(log('%s entered as %s' % (remarkname, username)))

        threading.Thread(target = handleRequest, args = (user,remarkname)).start()
    else:
        try:
            username_to_user[username].gotMessage(text)
        except KeyError:
            print(log('无效的消息:%s %s\n%s' % (remarkname, username, text)))

def handleRequest(user, remarkname):
    while True:
        try:
            number = int(user.getInput('请输入你的编号：'))
        except ValueError:
            user.sendMessage('这不是数字')
            continue
            
        if not(number >= 1 and number < len(players)):
            user.sendMessage('超出编号范围')
            continue
        break
        
    if not players[number]:
        players[number] = identity.pop()
        players[number].number = number
    player = players[number]
    player.user = user
    player.name = remarkname
    player.welcome()
    
    print(log('%s已经上线' % players[number].num()))

def mainLoop():
    global players, lastKilled, nRound,\
        prophet, guard, witch, wolves
    nRound = 0
    prophet, guard, witch, wolves = None, None, None, []
    
    for player in players[1:]:
        if isinstance(player, Prophet):
            prophet = player
        elif isinstance(player, Witch):
            witch = player
        elif isinstance(player, Guard):
            guard = player
        elif isinstance(player, WolfLeader):
            wolves.insert(0, player)
        elif isinstance(player, Wolf):
            wolves.append(player)
    
    while True:
        lastKilled = []
        nRound += 1

        broadcast('-----第%d天晚上-----' % (nRound-1))
        print(log('-----第%d天晚上-----' % (nRound-1)))
        broadcast('天黑请闭眼')
        playSound('天黑请闭眼')

        broadcast(CLR_STRING)
        
        moveFor(guard)
            
        for wolf in wolves:
            if not wolf.died:
                moveFor(wolf)
                break
        
        moveFor(witch)
        
        if witch == None:
            isGameEnded()
        
        moveFor(prophet)
        
        broadcast('-----第%d天-----' % nRound)
        print(log('-----第%d天-----' % nRound))
        broadcast('天亮啦')
        playSound('天亮了')
        
        agent = players[1]
        broadcast('%s将记录白天的情况' % agent.num())
        
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
            if not isinstance(explodedMan, Wolf):
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
    for wolf in wolves:
        wolf.message('狼人广播：' + string)

# Check the end of game
def isGameEnded():
    peopleCount = 0
    godCount = 0
    wolfCount = 0
    for player in players[1:]:
        if not player.died:
            if isinstance(player, Villager):
                peopleCount += 1
            elif player.good:
                godCount += 1
            else:
                wolfCount += 1
    
    if peopleCount == 0:
        broadcast('刀民成功，狼人胜利！')
        playSound('刀民成功')
    elif godCount == 0:
        broadcast('刀神成功，狼人胜利！')
        playSound('刀神成功')
    elif wolfCount == 0:
        broadcast('逐狼成功，平民胜利！')
        playSound('逐狼成功')
    else:
        return
    endGame()
    exit()

main()
