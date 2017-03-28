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

main()
