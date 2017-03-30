import threading
import queue

import itchat

from log import log

# Start listening
itchat.auto_login()
threading.Thread(target = itchat.run).start()

username_to_user = {} # Map Wechat user name to WechatUser object

class WechatUser:
    def __init__(self, username):
        '''
        username: Wechat username
        '''
        self.msg_queue = queue.Queue() # Queue for messages
        self.username = username # Wechat username

        # Update the mapping
        username_to_user[username] = self

    def got_message(self, message):
        '''
        Called when new message is reveived.
        '''
        self.msg_queue.put(message)

    def send_message(self, message):
        '''
        Send message to user.
        '''
        if not message:
            message = '\n'*25 + '清屏'
            
        itchat.send(message, toUserName = self.username)

    def receive_message(self):
        '''
        Get message from user.
        '''
        return self.msg_queue.get() # Will block when there's no new message

    def get_input(self, message):
        '''
        Send message and get reply.
        '''
        if message:
            self.send_message(message)
        return self.receive_message()

# Accept a new message from players
@itchat.msg_register(itchat.content.TEXT)
def listen_wechat_message(message):
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

        threading.Thread(target = handle_request, args = (user,remarkname)).start()
    
    # If it's other message
    else:
        try:
            username_to_user[username].got_message(text)
        except KeyError:
            print(log('无效的消息:%s %s\n%s' % (remarkname, username, text)))

def handle_request(user, remarkname):
    players = game_controller.players

    # Ask for remarkname if it's empty
    if not remarkname:
        remarkname = user.get_input('您没有备注名，请输入你的名字')
        print('%s 更名为 %s' % (user.username, remarkname))

    # Ask for the player's ID
    while True:
        try:
            player_id = int(user.get_input('请输入你的编号'))
        except ValueError:
            user.send_message('这不是数字')
            continue
            
        if not(1 <= player_id < len(players)):
            user.send_message('超出编号范围')
            continue

        if players[player_id]:
            user.send_message('该编号已被占用')
            continue

        break
    
    # Assign an identity
    players[player_id] = game_controller.identity.pop()
    
    # Assign variables
    player = players[player_id]
    player.player_id = player_id
    player.user = user
    player.name = remarkname

    # Send message
    player.welcome()
    print(log('%s 已经上线' % player.desc()))