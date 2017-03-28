import threading
import queue

import itchat

from log import log

itchat.auto_login()
threading.Thread(target = itchat.run).start()

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
    players = game_controller.players
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
        
    players[player_id] = game_controller.identity.pop() # Assign an identity
    
    player = players[player_id]
    player.player_id = player_id
    player.user = user
    player.name = remarkname

    player.welcome()
    
    print(log('%s已经上线' % players[player_id].num()))