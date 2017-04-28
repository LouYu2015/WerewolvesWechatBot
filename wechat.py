import threading
import queue
import time

import itchat

import client_control

class WechatController(client_control.ClientController):
    def __init__(self, game_controller):
        super().__init__(game_controller)

        self.username_to_user = {} # Map Wechat user name to WechatUser object
        self.send_msg_queue = queue.Queue() # Avoid sending messages too fast by buffering

        # Start listening Wechat messages
        itchat.auto_login()
        threading.Thread(target = itchat.run).start()

        # Send messages in another thread
        threading.Thread(target = self.send_messages_in_queue).start()

        # Accept new messages from players
        @itchat.msg_register(itchat.content.TEXT)
        def listen_wechat_message(message_info):
            username = message_info['User']['UserName'] # User name of the Wechat user
            text = message_info['Text'] # Content of the message
            self.got_message(username, text)

    def send_messages_in_queue(self):
        while(True):
            (username, message) = self.send_msg_queue.get()
            itchat.send(message, toUserName = username)

            time.sleep(0.5)

    def register_user(self, username, user):
        self.username_to_user[username] = user

    def user_from_username(self, username):
        try:
            return self.username_to_user[username]
        except KeyError:
            raise client_control.UserNotRegistered()

    def clear_screen(self, username):
        message = '\n'*25 + '清屏'
        self.send_message(username, message)

    def send_message(self, username, message):
        self.send_msg_queue.put((username, message))
