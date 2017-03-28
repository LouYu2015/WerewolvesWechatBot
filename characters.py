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
        return '%d号%s' % (self.number, self.name)
    
    def description(self):
        return '%d号%s%s' % (self.number, self.identity, self.name)
    
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