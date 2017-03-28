'''
Author: Yu Lou(louyu27@gmail.com)

A simple server program to test Werewolf client.
'''
import socket
import threading
import socket
from datatrans import sendData, receiveData
import time

port = int(input('输入服务器端口：'))
    
def handleRequest(sock):
    while True:
        cmd = input('输入要发送的指令:')
        if cmd == 'stop':
            sendData(sock, 'stop')
        elif cmd == 'input':
            sendData(sock, 'input')
            sendData(sock, input('要发送的内容：'))
            print(receiveData(sock))
        elif cmd == 'print':
            sendData(sock, 'print')
            sendData(sock, input('提示字符串：'))

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('0.0.0.0', port))
s.listen(5)

try:
    while True:
        sock, addr = s.accept()
        print(log('%s 连接到了服务器' % str(addr)))
        threading.Thread(target = handleRequest, args = (sock,)).start()
finally:
    s.close()
