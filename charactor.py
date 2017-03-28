from audio import playSound
from log import log

CLR_STRING = '\n'*25 + '清屏' # A string to clear screen on Wechat

def wait_for_random_time():
    time.sleep(random.random()*4+4)

class Character:
    def __init__(self, controller):
        '''
        controller: game controller
        '''
        self.player_id = None # ID of the player
        self.died = False # Is player died
        self.protected = False # Is player protected by Savior
        self.name = None # Player's name
        self.user = None # WechatUser object
        self.controller = controller # Game controller
    
    def welcome(self):
        '''
        Tell the player his/her identity.
        '''
        self.message('你是%s' % self.description())
    
    def message(self, message):
        '''
        Send message to player.
        '''
        self.user.sendMessage(message)

    def inputFrom(self, message):
        '''
        Get input from player with message as prompt.
        '''
        return self.user.getInput(message).strip()
    
    def selectFrom(self, string):
        '''
        Ask the player to select yes/no.
        '''
        while True:
            answer = self.inputFrom(string + '(y/n)：')

            if answer == 'Y' or answer == 'y':
                return True
            elif answer == 'N' or answer == 'n':
                return False
            else:
                self.message('请输入Y/y(yes)或者N/n(no)')
    
    def selectPlayer(self, string, min_id = 1):
        '''
        Let the player select a player.
        '''
        while True:
            try:
                answer = int(self.inputFrom(string + '：'))
            except ValueError:
                self.message('这不是数字')
                continue
                
            if not(min_id <= answer < len(self.controller.players)):
                self.message('超出编号范围')
                continue

            return answer
    
    def kill(self):
        '''
        Try to kill the player. Only werewolf should use this function.
        '''

        if not self.protected:
            self.die(True)
        else:
            self.controller.lastKilled.append(self)

        return self.died
    
    def die(self, killed_by_wolf = False):
        '''
        Called when the player will be died. Ignore Savior's protection.

        killed_by_wolf: whether killed by a wolf.
        '''
        self.died = True
        self.controller.lastKilled.append(self)

        if not killed_by_wolf:
            # If killed by wolf, game won't end until Witch makes a choice.
            self.controller.isGameEnded()
    
    def afterDying(self):
        '''
        Called at the start of daytime if the player died at night.
        '''
        pass
    
    def num(self):
        '''
        Short description of the player.
        '''
        return '%d号%s' % (self.player_id, self.name)
    
    def description(self):
        '''
        Description of the player.
        '''
        return '%d号%s%s' % (self.player_id, self.__class__.identity, self.name)
    
    def openEyes(self):
        '''
        Ask the player to open eyes.
        '''
        playSound('%s请睁眼' % self.__class__.identity)
    
    def closeEyes(self):
        '''
        Ask the player to close eyes.
        '''
        playSound('%s请闭眼' % self.__class__.identity)
        self.message(CLR_STRING)
    
class Witch(Character):
    identity = '女巫'
    good = True
    
    def __init__(self, controller):
        super().__init__(controller)
        self.usedPoison = False
        self.usedMedicine = False
    
    def move(self):
        if self.usedMedicine:
            self.message('你用过解药了')
        else:
            try:
                diedMan = self.controller.lastKilled[-1]
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

        self.controller.isGameEnded()
            
        if self.usedPoison:
            self.message('你用过毒药了')
            wait_for_random_time() # Won't let the player close eyes immediately

        else:
            if self.selectFrom('是否使用毒药'):
                target_id = self.selectPlayer('输入要毒死的玩家,0表示取消', min_id = 0)

                if target_id != 0:
                    target = self.controller.players[target_id]

                    target.die() # Can't be saved by Savior
                    target.can_use_gun = False
                    self.usedPoison = True

                    print(log('%s毒死了%s' % (self.description(), target.description())))

class Savior(Character):
    identity = '守卫'
    good = True
    
    def __init__(self, controller):
        super().__init__(controller)
        self.lastProtected = self.controller.players[0] # The player that was protected on last round
    
    def move(self):
        # Choose the target
        while True:
            target_id = self.selectPlayer('输入要守护的人,0表示空守', min_id = 0)
            target = self.controller.players[target_id]
            
            if target.player_id != 0 and target is self.lastProtected:
                self.message('连续的回合里不能守护同一个人')
                continue

            break

        # Protect the target
        self.lastProtected.protected = False
        target.protected = True
        self.lastProtected = target

        print(log('%s守护了%s' % (self.description(), target.description())))

class Seer(Character):
    identity = '预言家'
    good = True
    
    def move(self):
        # Choose the target
        while True:
            target_id = self.selectPlayer('选择你要预言的人')
            target = self.controller.players[target_id]

            if target.died and target not in self.controller.lastKilled:
                self.message('你不能验死人')
                continue

            break

        # Send the result
        if target.__class__.good:
            self.message('%s是好人' % target.num())
            print(log('%s发现%s是金水' % (self.description(), target.description())))
        else:
            self.message('%s是坏人' % target.num())
            print(log('%s发现%s是查杀' % (self.description(), target.description())))
            
class Hunter(Character):
    identity = '猎人'
    good = True

    def __init__(self, controller):
        super().__init__(controller)
        self.can_use_gun = True
    
    def afterDying(self):
        # Can't use gun if killed by Witch
        if not self.can_use_gun:
            self.message('你是被女巫毒死的，不能放枪')
            return
        
        # Choose target
        target_id = self.selectPlayer('输入你要枪杀的玩家，0表示不放枪', min_id = 0)
        
        if target_id == 0:
            print(log('猎人没有放枪'))
            return
        
        target = self.controller.players[target_id]
        
        # Send result
        broadcast('%s枪杀了%s' % (self.description(), target.num()))
        print(log('%s枪杀了%s' % (self.description(), target.description())))
        target.die()

class Werewolf(Character):
    identity = '狼人'
    good = False
    
    def move(self):
        self.controller.broadcastToWolves('由%s代表狼人进行操作' % self.description())

        # Choose target
        target_id = self.selectPlayer('输入你要杀的玩家，0表示空刀', min_id = 0)

        if target_id == 0:
            self.controller.broadcastToWolves('狼人选择空刀')
            print(log('狼人空刀'))
            return
        target = self.controller.players[target_id]

        # Kill
        target.kill()

        # Send result
        self.controller.broadcastToWolves('狼人选择刀%s' % target.num())
        print(log('狼人刀%s' % target.description()))
    
    def afterExploded(self):
        self.message('你不能带人')

class WerewolfLeader(Werewolf):
    identity = '狼王'
    
    def afterExploded(self):
        if self.selectFrom('是否要带人'):
            target_id = self.selectPlayer('输入你要带走的人')
            target = self.controller.players[target_id]

            target.die()
            
            broadcast('%s带走了%s' % (self.description(), target.num()))
            print(log('%s带走了%s' % (self.description(), target.description())))
        
    def openEyes(self):
        playSound('狼人请睁眼')
    
    def closeEyes(self):
        playSound('狼人请闭眼')
        
class Villager(Character):
    identity = '村民'
    good = True
