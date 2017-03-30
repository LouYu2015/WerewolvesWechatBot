from audio import play_sound
from log import log

class Character:
    def __init__(self, controller):
        '''
        controller: game controller
        '''
        self.player_id = None # ID of the player
        self.name = None # Player's name
        self.user = None # WechatUser object

        self.died = False # Is player died
        self.protected = False # Is player protected by Savior

        self.is_mayor = False # Is the player elected as a mayor

        self.controller = controller # Game controller
    
    def welcome(self):
        '''
        Tell the player his/her identity.
        '''
        self.message('你是 %s' % self.description())
    
    def message(self, message = ''):
        '''
        Send message to player.
        '''
        self.user.send_message(message)

    def get_input(self, message = ''):
        '''
        Get input from player with message as prompt.
        '''
        return self.user.get_input(message).strip()
    
    def decide(self, message = ''):
        '''
        Ask the player to select yes/no.
        '''
        if message:
            message += '(y/n)'

        answer = self.get_input(message)

        while True:
            if answer == 'Y' or answer == 'y':
                return True
            elif answer == 'N' or answer == 'n':
                return False
            else:
                self.message('请输入Y/y(yes)或者N/n(no)')
    
    def select_player(self, message = '', min_id = 1, candidates = None):
        '''
        Let the player select a player.
        '''
        # Default candidates
        if candidates == None:
            candidates = [player for player in self.controller.players[1:] \
                if not player.died or player in self.controller.killed_players]

        while True:
            try:
                answer = int(self.get_input(message))

            # Special cases
            except ValueError:
                self.message('这不是数字')
                continue
                
            if not(min_id <= answer < len(self.controller.players)):
                self.message('超出编号范围')
                continue

            if answer != 0 and self.controller.players[answer] not in candidates:
                self.message('不是候选人')
                continue

            # Return the result
            return answer
    
    def kill(self):
        '''
        Try to kill the player. Only werewolf should use this method.
        '''
        if not self.protected:
            self.die(True)
        else:
            self.controller.killed_players.append(self)
    
    def die(self, killed_by_wolf = False):
        '''
        Called when the player will be died. Ignore Savior's protection.

        killed_by_wolf: whether killed by a werewolf.
        '''
        self.died = True
        self.controller.killed_players.append(self)

        if not killed_by_wolf: # If killed by wolf, game won't end until Witch makes a choice.
            self.controller.is_game_ended()
    
    def after_dying(self):
        '''
        Called at the start of daytime if the player died at night.
        '''
        if self.is_mayor:
            # Resign
            self.is_mayor = False
            self.controller.have_mayor = False

            # Select next Mayor
            self.controller.broadcast('等待移交警徽')
            next_mayor_id = self.select_player('输入你要移交警徽的玩家，撕警徽用 0 表示', min_id = 0)
            
            # Assign next mayor and broadcast the result
            if next_mayor_id == 0:
                self.controller.broadcast('警长 %s 选择撕警徽' % self.desc())
            else:
                next_mayor = self.controller.players[next_mayor]
                next_mayor.is_mayor = True
                self.controller.have_mayor = True

                self.controller.broadcast('警长 %s 选择把警徽交给 %s' % (self.desc(), next_mayor.desc()))
    
    def desc(self):
        '''
        Short description of the player.
        '''
        return '%d号%s' % (self.player_id, self.name)
    
    def description(self):
        '''
        Description of the player.
        '''
        return '%d号%s%s' % (self.player_id, self.__class__.identity, self.name)
    
    def open_eyes(self):
        '''
        Ask the player to open eyes.
        '''
        play_sound('%s请睁眼' % self.__class__.identity)
    
    def close_eyes(self):
        '''
        Ask the player to close eyes.
        '''
        play_sound('%s请闭眼' % self.__class__.identity)

        # Clear screen
        self.message()
    
class Witch(Character):
    identity = '女巫'
    good = True
    
    def __init__(self, controller):
        super().__init__(controller)
        self.used_poison = False
        self.used_medicine = False
    
    def move(self):
        used_medicine_this_round = self.use_medicine()
        
        self.controller.is_game_ended()
        
        if used_medicine_this_round:
            self.message('不能双开')
        else:
            self.use_poison()

    def use_medicine(self):
        # Check whether medicine is used
        if self.used_medicine:
            self.message('你用过解药了')
            self.controller.wait_random_time() # Won't let the player close eyes immediately
            return False

        # Find the died player
        try:
            died_player = self.controller.killed_players[-1]
        except IndexError:
            self.message('刚才是空刀')
            self.controller.wait_random_time()
            return False

        # Tell the Witch
        self.message('刚才 %s 被杀了' % died_player.desc())

        # Witch can't save himself/herself after fist round
        if (self.controller.nRound >= 2 and died_player is self):
            self.message('第二回合起你不能自救')
            return False

        # Ask whether the Witch want's to use medicine
        if not self.decide('是否使用解药'):
            print(log('%s 没有使用解药' % self.description()))
            return False

        else:
            print(log('%s 救了 %s' % (self.description(), died_player.description())))
            died_player.died = False
            
            # If Witch saves the protected player, the player will die
            if died_player.protected:
                print(log('同守同救！'))
                died_player.died = True

            self.used_medicine = True
            return True

    def use_poison(self):
        # Check whether poison is used
        if self.used_poison:
            self.message('你用过毒药了')
            self.controller.wait_random_time() # Won't let the player close eyes immediately
            return False

        # Ask whether the Witch want's to use poison
        if not self.decide('是否使用毒药'):
            print(log('%s 没有使用毒药' % self.description()))
            return False

        # Ask whoever the Witch wants to kill
        target_id = self.select_player('输入要毒死的玩家,0表示取消', min_id = 0)

        if target_id != 0:
            target = self.controller.players[target_id]

            target.die() # Can't be saved by Savior
            target.can_use_gun = False

            print(log('%s 毒死了 %s' % (self.description(), target.description())))
            self.used_poison = True
            return True

class Savior(Character):
    identity = '守卫'
    good = True
    
    def __init__(self, controller):
        super().__init__(controller)
        self.last_protected = self.controller.players[0] # The player that was protected on last round
    
    def move(self):
        # Choose the target
        while True:
            target_id = self.select_player('输入要守护的人,0表示空守', min_id = 0)
            target = self.controller.players[target_id]
            
            if target.player_id != 0 and target is self.last_protected:
                self.message('连续的回合里不能守护同一个人')
                continue
            else:
                break

        # Protect the target
        self.last_protected.protected = False
        target.protected = True
        print(log('%s守护了%s' % (self.description(), target.description())))

        self.last_protected = target


class Seer(Character):
    identity = '预言家'
    good = True
    
    def move(self):
        # Choose the target
        target_id = self.select_player('选择你要预言的人')
        target = self.controller.players[target_id]

        # Tell the result
        if target.__class__.good:
            self.message('%s 是好人' % target.desc())
            print(log('%s 发现 %s 是金水' % (self.description(), target.description())))
        else:
            self.message('%s 是坏人' % target.desc())
            print(log('%s 发现 %s 是查杀' % (self.description(), target.description())))
            
class Hunter(Character):
    identity = '猎人'
    good = True

    def __init__(self, controller):
        super().__init__(controller)
        self.can_use_gun = True
    
    def after_dying(self):
        super().after_dying()

        # Can't use gun if killed by Witch
        if not self.can_use_gun:
            self.message('你是被女巫毒死的，不能放枪')
            return
        
        # Choose target
        target_id = self.select_player('输入你要枪杀的玩家编号，0表示不放枪', min_id = 0)
        target = self.controller.players[target_id]
        
        if target_id == 0:
            print(log('猎人没有放枪'))
            return
        
        # Broadcast the result
        broadcast('%s 枪杀了 %s' % (self.description(), target.desc()))
        print(log('%s 枪杀了 %s' % (self.description(), target.description())))
        target.die()

class Werewolf(Character):
    identity = '狼人'
    good = False
    
    def move(self):
        self.controller.broadcast_to_wolves('由 %s 代表狼人进行操作' % self.description())

        # Choose target
        target_id = self.select_player('输入你要杀的玩家，0表示空刀', min_id = 0)
        target = self.controller.players[target_id]

        if target_id == 0:
            self.controller.broadcast_to_wolves('狼人选择空刀')
            print(log('狼人空刀'))
            return

        # Kill
        target.kill()

        # Send result
        self.controller.broadcast_to_wolves('狼人选择刀 %s' % target.desc())
        print(log('狼人刀 %s' % target.description()))
    
    def after_exploded(self):
        self.message('你不能带人')

class WerewolfLeader(Werewolf):
    identity = '狼王'
    
    def after_exploded(self):
        if self.decide('是否要带人'):
            target_id = self.select_player('输入你要带走的人')
            target = self.controller.players[target_id]

            target.die()
            
            broadcast('%s 带走了 %s' % (self.description(), target.desc()))
            print(log('%s 带走了 %s' % (self.description(), target.description())))
        
    def open_eyes(self):
        play_sound('狼人请睁眼')
    
    def close_eyes(self):
        play_sound('狼人请闭眼')
        self.message('')
        
class Villager(Character):
    identity = '村民'
    good = True
