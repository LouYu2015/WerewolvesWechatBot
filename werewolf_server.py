'''
A Wechat bot for the Werewolf game, running on Python 3.

Contributor(s): Yu Lou(louyu27@gmail.com)
'''

import socket
import time
import random
import struct
import threading

import audio
from audio import play_sound
from charactor import *
import wechat
import config_editor

audio.audioPath = 'audio'

def main():
    controller = GameController()
    wechat.game_controller = controller

    controller.get_ready()
    play_sound('游戏开始')
    controller.main_loop()

class WerewolfExploded(Exception):
    '''
    Raised when a werewolf explodes.
    '''
    def __init__(self, player):
        '''
        player: the werewolf that explodes
        '''
        self.player = player

class GameController:
    def __init__(self):
        # Game related variables
        self.have_mayor = False # Does mayor currently exist
        self.identity_list = [] # List of possible identities

        # Other variables
        self.history = [] # History of status messages
        self.game_started = False # Is game started?
        self.config = config_editor.Config('config.json', 'config_prompts.json') # Configurations
        self.event_start_game = threading.Event()

        self.initialize_identity_pool()

    # Manage identities
    def initialize_identity_pool(self):
        '''
        Initialize 'identity_list' and 'identity_pool' from \
        the configuration in 'self.config'.
        '''
        self.identity_list = []
        path_to_class = [ # Map configuration path to class name
            ('gods/have_witch', Witch),
            ('gods/have_seer', Seer),
            ('gods/have_savior', Savior),
            ('gods/have_hunter', Hunter),
            ('gods/have_idiot', Idiot),
            ('gods/have_silencer', Silencer),
            ('n_villager', Villager),
            ('werewolves/have_werewolf_leader', WerewolfLeader),
            ('werewolves/n_werewolf', Werewolf)
            ]

        for (path, identity) in path_to_class:
            value = self.config(path) # Number of corresponding identity

            # Add charactors
            if isinstance(value, bool):
                if value == True:
                    self.identity_list.append(identity(controller = self))
            else:
                for i in range(value):
                    self.identity_list.append(identity(controller = self))

        self.identity_pool = self.identity_list.copy()

    def reassign_identities(self):
        '''
        Reassign identities for players.
        '''
        self.initialize_identity_pool()

        old_player_list = self.players
        self.players = [Villager(self)] + [None]*len(self.identity_pool)

        for (i, player) in enumerate(old_player_list):
            if player and i != 0:
                # Assign a new identity
                new_identity = self.pop_from_identity_pool()

                # Copy parameters
                new_identity.player_id = player.player_id
                new_identity.user = player.user
                new_identity.name = player.name

                # Add to player list
                try:
                    self.players[new_identity.player_id] = new_identity

                # If the ID is too large, ask for a new ID
                except IndexError:
                    new_identity.get_id()
                    self.players[new_identity.player_id] = new_identity

                # Inform the player
                new_identity.welcome()

    def pop_from_identity_pool(self):
        '''
        Get an identity from identity pool.
        '''
        identity = random.choice(self.identity_pool)
        self.identity_pool.remove(identity)
        return identity

    def str_identity_list(self):
        '''
        Get a string representation of identity list.
        '''
        str_list = ','.join([player.identity for player in self.identity_list])
        return '当前角色配置为%s' % str_list

    # Main program
    def get_ready(self):
        # Initialize player list
        self.players = [Villager(self)] + [None]*len(self.identity_pool)
        self.players[0].died = True # Player 0 is just a placeholder
        self.players[0].player_id = 0

        # Wait for players to join the game
        while True:
            self.event_start_game.clear()
            self.event_start_game.wait()

            can_proceed = True
            for (i, player) in enumerate(self.players[1:]):
                if player == None or not player.ready:
                    self.broadcast('缺少 %d 号玩家' % (i+1))
                    can_proceed = False

            if can_proceed:
                break

    def main_loop(self):
        self.game_started = True

        # Initialize variables
        self.nRound = 0 # Number of days elapsed
        seer, savior, witch, silencer, self.werewolves = None, None, None, None, []
        self.killed_players = [] # List of players who are killed last night
        
        # Find players who have special identities
        for player in self.players[1:]:
            if isinstance(player, Seer):
                seer = player
            elif isinstance(player, Witch):
                witch = player
            elif isinstance(player, Savior):
                savior = player
            elif isinstance(player, Silencer):
                silencer = player
            elif isinstance(player, WerewolfLeader):
                self.werewolves.insert(0, player) # Insert the leader to the front
            elif isinstance(player, Werewolf):
                self.werewolves.append(player)
        
        # Main loop
        while True:
            self.nRound += 1

            # Night
            self.status('-----第%d天晚上-----' % self.nRound, broadcast = True)

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

            self.move_for(silencer)
            
            # Day
            self.status('-----第%d天-----' % self.nRound, broadcast = True)

            self.broadcast('天亮啦')
            play_sound('天亮了')
            
            # Vote for Mayor
            if self.nRound == 1 and self.config('rules/have_mayor'):
                self.vote_for_mayor()
            
            # Remove players who resurrect
            self.killed_players = [player for player in self.killed_players if player.died]
            random.shuffle(self.killed_players)

            # Show the result of last night
            if self.killed_players:
                self.broadcast('昨天晚上，%s 死了' % self.player_list_to_str(self.killed_players))
            else:
                self.broadcast('昨天晚上是平安夜～')

            # Trigger after-dying action
            for player in self.killed_players:
                player.after_dying()

            # Trigger wake-up action
            player_list = self.survived_players()
            random.shuffle(player_list)

            for player in player_list:
                player.wake_up()
            
            # Vote for suspect
            self.vote_for_suspect()

            # Reset killed_players
            self.killed_players = []

    def move_for(self, charactor):
        '''
        Called when a charactor needs to take a move.

        charactor: the charactor that needs to take a move
        '''
        if charactor == None:
            return

        charactor.open_eyes()

        if not charactor.died or charactor in self.killed_players:
            charactor.move()
        else:
            # Won't let the player close eyes immediately even if he/she died.
            time.sleep(random.random()*4+4) 

        charactor.close_eyes()

    def is_game_ended(self):
        '''
        Show game result if game ends.
        '''
        # if self.nRound == 1:
        #     return

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
            self.status('刀民成功，狼人胜利！', broadcast = True)
            play_sound('刀民成功')
        elif god_count == 0:
            self.status('刀神成功，狼人胜利！', broadcast = True)
            play_sound('刀神成功')
        elif werewolf_count == 0:
            self.status('逐狼成功，平民胜利！', broadcast = True)
            play_sound('逐狼成功')
        else:
            return

        # End of game
        self.status('游戏结束', broadcast = True)
        self.broadcast(self.get_history())
        exit()

    def get_history(self):
        '''
        Show player identites status history.
        '''
        # Get desciptions of each player
        identity_desc = [player.description() for player in self.players[1:]]

        # Show player identites and status history
        return '\n'.join(identity_desc + self.history)

    # Voting system
    def vote_for_mayor(self):
        '''
        Ask players to vote for a Mayor.
        '''
        targets = self.players[1:]

        # Ask for candidates
        initial_candidates = self.broadcast_choice('是否竞选警长', '%s 完成了是否竞选的选择', targets = targets)

        self.status('%s 竞选警长' % self.player_list_to_str(initial_candidates), broadcast = True)

        # Decide who can vote
        can_vote_players = [player for player in targets \
            if player not in initial_candidates]

        # Decide speech order
        if initial_candidates:
            self.decide_speech_order(initial_candidates)

        # Special case: no candidate
        if not initial_candidates:
            return

        # Ask candidates whether they want to quite
        self.broadcast('正在等待候选人选择是否继续竞选')
        candidates = self.broadcast_choice('是否继续竞选', '%s 完成了是否继续竞选的选择', targets = initial_candidates)
        
        quited_player = [player for player in initial_candidates if player not in candidates]

        # Show remaining candidates
        self.status('%s 退水' % self.player_list_to_str(quited_player), broadcast = True)
        self.status('%s 继续竞选警长' % self.player_list_to_str(candidates), broadcast = True)

        # Check for special situations
        # No candidate
        if not candidates:
            return

        if not can_vote_players:
            self.status('没有人可以投票', broadcast = True)
            return

        # Just one candidate
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
        self.status('%s 当选警长' % mayor.description())

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
            self.status('%s 爆炸' % werewolf.description())

            werewolf.after_dying()
            werewolf.after_exploded()
        
        # Vote out the suspect
        else:
            if suspect.can_be_voted_out:
                self.broadcast('%s 被投出' % suspect.desc())
                self.status('%s 被投出' % suspect.description())
                suspect.die()
                suspect.after_dying()
            else:
                self.broadcast('%s 不能被投出' % suspect.desc())
                self.status('%s 不能被投出' % suspect.description())

        self.is_game_ended()

        # Give players some time to view the result
        self.broadcast_choice('查看结果后，回复y以继续游戏', '%s 已确认今天的结果', targets = targets)

    def decide_speech_order(self, candidates):
        '''
        Randomly choose an order for players to give a speech.

        candidate: list of players who can give a speech.
        '''
        first_player = random.choice(candidates)
        direction = random.choice(['顺时针', '逆时针'])
        self.broadcast('从 %s %s发言' % (first_player.desc(), direction))

    def broadcast_choice(self, message, finish_message, targets = None):
        '''
        Ask several players to choose yes/no at the same time.

        message: message that describes choices.
        finish_message: status message for players who finished choice
        targets: list of players that needs to make the choice.

        Return a list of players who choose yes.
        '''
        accepted_players = []
        first_respond_event = threading.Event() # Set when first respond is received
        broadcast_event = threading.Event() # Set when it's time to reveal the result
        finish_events = [] # Set when the player finishes voting

        def ask_for_choice(player, finish_event):
            if player.decide(message):
                accepted_players.append(player)
            
            player.message('收到')
            first_respond_event.set()
            
            broadcast_event.wait()
            self.players[1].message(finish_message % player.desc())

            finish_event.set()

        # Collect reply
        for player in targets:
            finish_event = threading.Event()
            finish_events.append(finish_event)

            threading.Thread(target = ask_for_choice, args = (player,finish_event)).start()

        # Broadcast status after some time
        first_respond_event.wait()
        time.sleep(self.config('system/vote_waiting_time'))
        broadcast_event.set()

        # Wait for all players to finish
        for event in finish_events:
            event.wait()

        return accepted_players

    def vote(self, candidates, message, min_id = 1, targets = None):
        '''
        Ask players to vote.

        candidates: list of players who can be voted.
        message: prompt message.
        min_id: minimum player id that voters can choose.
        targets: list of players who can vote.

        Return the player who has the highest vote.
        '''
        while True:
            # Get and show result
            (vote_statistic, give_up) = self.get_vote_statistic(candidates, message, min_id, targets = targets)
            self.show_vote_result(vote_statistic, give_up)
            
            # Check if two people get equal votes
            try:
                if vote_statistic[0][2] == vote_statistic[1][2]:
                    self.broadcast('票数相同，重新投票')
                    continue
                else:
                    break
            except IndexError:
                break

        return vote_statistic[0][0]

    def get_vote_statistic(self, candidates, message, min_id = 1, targets = None):
        '''
        Ask players to vote.

        candidates: list of players who can be voted.
        message: prompt message.
        min_id: minimum player id that voters can choose.
        targets: list of players who can vote.

        Return a list of tuple and a list of players who give up.
        Elements in each tuple:
            [0]:candidate
            [1]:list of players who voted for this candidate
            [2]:vote count for this candidate
        '''
        voted_for = [list() for i in range(len(self.players) + 1)]
        vote_count = [0]*(len(self.players) + 1)
        give_up = []

        # Ask for vote
        vote_result = self.get_vote_result(candidates, message, min_id, targets)

        # Count votes
        for (voter, elected_id) in vote_result:
            if elected_id == 0:
                raise WerewolfExploded(voter)
            elif elected_id == -1:
                give_up.append(voter)
                continue

            # Count votes
            voted_for[elected_id].append(voter)

            if voter.is_mayor:
                vote_count[elected_id] += 1.5
            else:
                vote_count[elected_id] += 1

        # Sort votes
        vote_statistic = [(candidate, voted_for[candidate.player_id], vote_count[candidate.player_id]) \
            for candidate in candidates]
        vote_statistic.sort(key = lambda x: x[2], reverse = True)

        return (vote_statistic, give_up)

    def get_vote_result(self, candidates, message, min_id, targets):
        vote_result = []
        first_respond_event = threading.Event() # Set when first respond is received
        broadcast_event = threading.Event() # Set when it's time to reveal the result
        finish_events = [] # Set when the player finishes voting

        def ask_for_vote(player, finish_event):
            if player.decide('是否投票'):
                while True:
                    voted_id = player.select_player(message, min_id = min_id, candidates = candidates)

                    # Vote for number 0 means explode
                    if voted_id == 0:
                        if player.good or not self.config('rules/werewolf_can_explode'):
                            player.message('你不能爆炸')
                            continue
                    
                    vote_result.append((player, voted_id))
                    break
            else:
                vote_result.append((player, -1))

            player.message('收到')
            first_respond_event.set()

            broadcast_event.wait()
            self.players[1].message('%s 已投票' % player.desc())

            finish_event.set()

        # Ask for vote
        for player in targets:
            finish_event = threading.Event()
            finish_events.append(finish_event)

            threading.Thread(target = ask_for_vote, args = (player, finish_event)).start()

        # Boradcast status after some time
        first_respond_event.wait()
        time.sleep(self.config('system/vote_waiting_time'))
        broadcast_event.set()

        # Wait for vote
        for event in finish_events:
            event.wait()

        return vote_result

    def show_vote_result(self, vote_results, give_up):
        '''
        Broadcast voting result.

        vote_results: the list returned by 'get_vote_statistic'
        give_up: list of players who give up voting
        '''
        messages = []

        for player in give_up:
            messages.append('%s 弃票' % player.desc())

        for vote_statistic in vote_results:
            # Unpack data
            player = vote_statistic[0]
            voted_by = vote_statistic[1]
            vote_count = vote_statistic[2]

            # Get string representation of voted_by
            str_voted_by = self.player_list_to_str(voted_by)

            # Broadcast the message
            messages.append('%s 获得 %.1f 票（%s）' % (player.desc(), float(vote_count), str_voted_by))

        self.broadcast('\n'.join(messages))

    # Message system
    def broadcast(self, message, targets = None):
        '''
        Broadcast a message. If 'targets' is 'None', broadcast to all players.

        message: the message to be broadcasted
        targets: list of players to receive this message
        '''
        # Default target
        if targets == None:
            targets = self.players[1:]

        # Broadcast the message
        for player in targets:
            if player:
                player.message(message)

    def broadcast_to_wolves(self, message):
        '''
        Broadcast a message to werewolves.
        '''
        self.broadcast('狼人：' + message, targets = self.werewolves)

    def status(self, message, broadcast = False):
        '''
        Store a status message.

        message: the status message
        broadcast: if 'True', the message will be broadcasted to players.
        '''
        message_with_time = '[%s]%s' % (time.strftime('%H:%M:%S'), message)
        self.history.append(message_with_time)
        print(message_with_time)

        if broadcast:
            self.broadcast(message)

    # Other methods
    def survived_players(self):
        '''
        Get a list of survivied players
        '''
        return [player for player in self.players[1:] if not player.died]

    def wait_random_time(self):
        '''
        Wait for a random amount of time.
        '''
        time.sleep(random.random()*4+4)

    def player_list_to_str(self, players):
        '''
        Convert a list of player to a string representation of it.

        players: list of players

        Return the string.
        '''
        if not players:
            result = '没有人'
        else:
            result = ','.join([player.desc() for player in players])

        return result

main()