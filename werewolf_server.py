'''
Author: Yu Lou(louyu27@gmail.com)

Server side program for the Werewolf game, running on Python 3.
'''
import socket
import threading
import time
import random
import struct

import audio
from audio import playSound
from datatrans import sendData, receiveData

audio.audioPath = '/home/louyu/werewolf/'

def main():
    global eventNewPlayer, players, identity
    
    eventNewPlayer = threading.Event()
    
    print('输入服务器端口：', end = '')
    port = int(input())

    players = [People()]# Player no.0 is not real
    players[0].number = 0

    identity = [People(), People(), People(),\
        Witch(), Prophet(), Guard(),\
        Wolf(), Wolf(), Wolf()]# Identities for each player
    random.seed(time.time())
    random.shuffle(identity)

    players += [None]*len(identity)

    threading.Thread(target = listenRequest, args = (port,)).start()

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

def listenRequest(port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('0.0.0.0', port))
        s.listen(5)
        while True:
            sock, addr = s.accept()
            print(log('%s 加入了游戏' % str(addr)))
            #print sock.recv(1000)
            threading.Thread(target = handleRequest, args = (sock,)).start()
    except socket.error as err:
        print('网络错误！')
        print(err)

def handleRequest(sock):
    while True:
        try:
            number = int(sendInput(sock, '请输入你的编号：'))
        except ValueError:
            sendPrint(sock,'这不是数字')
            continue
            
        if not(number >= 1 and number < len(players)):
            sendPrint(sock,'超出编号范围')
            continue
        break
        
    if not players[number]:
        players[number] = identity.pop()
        players[number].number = number
    player = players[number]
    player.sock = sock
    player.name = sendInput(sock, '请输入你的名字：')
    player.welcome()
    
    print(log('%s已经上线' % players[number].num()))
    eventNewPlayer.set()

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

# Interact with client
def sendStop(sock):# Stop client
    sendData(sock, 'stop')

def sendPrint(sock, string):# Send message to client
    sendData(sock, 'print')
    sendData(sock, string)

def sendInput(sock, string):# Receive input from client
    sendData(sock, 'input')
    sendData(sock, string)
    return receiveData(sock)

# Add time to message
def log(string):
    return '[%s]%s' % (time.strftime('%H:%M:%S'), string)

# Broadcast
def broadcast(string):
    for player in players[1:]:
        player.message('全员广播：' + string)

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
            if isinstance(player, People):
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

def endGame():
    for player in players[1:]:
        sendStop(player.sock)

# Characters
class Character:
    def __init__(self):
        self.sock = None # Socket connection
        self.number = None # Order number of the player
        self.died = False # Is player died
        self.protected = False # Is player protected by Guard
        self.good = None # Is player good or bad
        self.name = '' # Player's name
        self.identity = '' # Player's character name
    
    def welcome(self):# Tell the player his/her identity
        self.message('你是%s' % self.description())
    
    def message(self, string): # Send message to player
        while True:
            try:
                sendPrint(self.sock, log(string))
                return
            except socket.error:
                eventNewPlayer.clear()
                print(log('%s掉线了！' % self.num()))
                if self.died and self not in laskKilled:
                    print(log('该玩家已死亡，忽略该玩家'))
                    return
                playSound('有人掉线了')
                eventNewPlayer.wait()
                continue
    
    def inputFrom(self, string):# Get input from player
        while True:
            try:
                return sendInput(self.sock, log(string)).strip()
            except (socket.error, struct.error):
                eventNewPlayer.clear()
                print(log('%s掉线了！' % self.num()))
                playSound('有人掉线了')
                eventNewPlayer.wait()
                continue
            except UnicodeDecodeError:
                print(log('%s出现了编码错误！' % self.description()))
                self.message('编码错误！')
                continue
    
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
        return '%d号%s' % (self.number, self.name)
    
    def description(self):
        return '%d号%s%s' % (self.number, self.identity, self.name)
    
    def openEyes(self):
        playSound('%s请睁眼' % self.identity)
    
    def closeEyes(self):
        playSound('%s请闭眼' % self.identity)
    
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

class Guard(Character):
    def __init__(self):
        super().__init__()
        self.identity = '守卫'
        self.good = True
        self.lastProtected = players[0]
    
    def move(self):
        while True:
            protectedMan = self.selectPlayer('输入要守护的人,0表示空守', minNumber = 0)
            protectedMan = players[protectedMan]
            
            if protectedMan.number != 0 and protectedMan is self.lastProtected:
                self.message('连续的回合里不能守护同一个人')
                continue
            break
        self.lastProtected.protected = False
        protectedMan.protected = True
        print(log('%s守护了%s' % (self.description(), protectedMan.description())))
        
        self.lastProtected = protectedMan

class Prophet(Character):
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

class Wolf(Character):
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

class WolfLeader(Wolf):
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
        
class People(Character):
    def __init__(self):
        super().__init__()
        self.identity = '村民'
        self.good = True

main()
