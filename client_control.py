import queue
import threading

class UserNotRegistered(Exception):
    """
    Raised when the Client object of an unregistered user is requested.
    """
    pass

class Client:
    def __init__(self, controller, username):
        '''
        controller: Client controller
        username: Username
        '''
        self.controller = controller
        self.username = username
        self.remarkname = None

        self.identity = None # Link to the Charactor object of the user
        self.msg_queue = queue.Queue() # Queue for received messages from user
        self.ready = False # Is user ready to begin the game

    def clear_queue(self):
        '''
        clear message queue.
        '''
        try:
            while True:
                self.msg_queue.get(block = False)
        except queue.Empty:
            return

    def got_message(self, message):
        '''
        Put message into message queue.
        Will be called by controller when a new message arrives.
        '''
        self.msg_queue.put(message)

    def send_message(self, message):
        '''
        Send message to user.
        '''
        if message:
            self.controller.send_message(self.username, message)
        else:
            self.controller.clear_screen(self.username)

    def receive_message(self):
        '''
        Return the next message from user.
        '''
        return self.msg_queue.get() # Will block when there's no new message

    def get_input(self, prompt):
        '''
        Send prompt and return the reply.
        '''
        if prompt:
            self.send_message(prompt)

        self.clear_queue()

        return self.receive_message()

    def get_int(self, prompt, min_value = -float('inf'), max_value = float('inf')):
        '''
        Ask the user to enter an integer in range(min_value, max_value).
        Return the integer.
        '''
        while True:
            try:
                result = int(self.get_input(prompt))
            except ValueError:
                self.send_message('这不是数字')
                continue
                
            if not(min_value <= result < max_value):
                self.send_message('超出范围')
                continue

            return result

    def decide(self, message = ''):
        '''
        Ask the player to select yes/no.
        Return a boolean.
        '''
        if message:
            message += '(y/n)'

        while True:
            answer = self.get_input(message)

            if answer == 'Y' or answer == 'y':
                return True
            elif answer == 'N' or answer == 'n':
                return False
            else:
                self.send_message('请输入Y/y(yes)或者N/n(no)')

class ClientController:
    def __init__(self, game_controller):
        """
        game_controller: link to the game controller.
        """
        self.game_controller = game_controller

    def new_user(self, username):
        """
        Initiate a new user.

        username: username of the user
        """
        return Client(self, username)

    def register_user(self, username, user):
        """
        Link the user object to the username.
        """
        pass

    def user_from_username(self, username):
        """
        Return the user object that has the username.
        """
        return None

    def clear_screen(self, username):
        """
        Clear the screen of the user.
        """
        pass

    def send_message(self, username, message):
        """
        Send a message to the user.
        """
        pass

    def got_message(self, username, message):
        """
        Process the message from user.
        Will be called by message listener upon message arrival.
        """
        if '进入游戏' in message:
            threading.Thread(target = self.enter_game, args = (username,)).start()
            return

        try:
            user = self.user_from_username(username)
        except UserNotRegistered:
            print('收到未注册用户发送的消息')
            return

        is_command = self.process_command(user, message)

        if not is_command:
            user.got_message(message)

    def process_command(self, user, message):
        """
        If the message is a command, execute the command.

        Return whether the message is a command.
        """
        # Edit configuration
        if '编辑配置' in message:
            command = self.edit_config

        # See identities
        elif '查看配置' in message:
            command = self.get_identity_list

        # Start game
        elif '开始游戏' in message:
            command = self.start_game

        # Get game history
        elif '接管上帝' in message:
            command = self.get_game_history

        else:
            command = None

        if command:
            threading.Thread(target = command, args = (user,)).start()
            return True
        else:
            return False

    def enter_game(self, username):
        # Check whether user have registered
        try:
            user = self.user_from_username(username)
        except UserNotRegistered:
            pass
        else:
            user.send_message('您已经注册过了')
            return

        user = self.new_user(username)
        self.register_user(username, user)

        players = self.game_controller.players

        # Ask for remarkname
        remarkname = user.get_input('请输入你想使用的备注名')

        user.remarkname = remarkname
        print('%s 进入游戏' % remarkname)
        
        # Assign an identity
        player = self.game_controller.pop_from_identity_pool()
        user.identity = player

        # Assign properties
        player.user = user
        player.name = remarkname
        player.get_id()

        players[player.player_id] = player

        # Tell the identity
        player.welcome()

    def edit_config(self, user):
        if self.game_controller.game_started:
            user.send_message('游戏过程中不能编辑配置')
            return

        user.ready = False

        self.game_controller.config.edit(user)

        self.game_controller.status('配置已更新', broadcast = True)
        self.game_controller.reassign_identities()
        user.ready = True

    def get_identity_list(self, user):
        user.identity.welcome()

    def start_game(self, user):
        self.game_controller.event_start_game.set()

    def get_game_history(self, user):
        if self.game_controller.game_started:
            user.send_message(self.game_controller.get_history())
            self.game_controller.broadcast('%s 接管上帝' % user.remarkname)
