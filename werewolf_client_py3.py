# -*- coding: UTF-8 -*-
'''
Author: Yu Lou(louyu27@gmail.com)

Client side program for Werewolf game, running on Python 3.x.
'''
import socket
import struct
import sys, locale
from datatrans import sendData, receiveData

while True:
    try:
        ip = input('输入服务器地址:')
        port = int(input('输入服务器端口:'))

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, port))
    except socket.error as error:
        print('链接时遇到问题，请重试。')
        print(error)
        print('')
    else:
        break

while True:
    cmd = receiveData(s)
    if cmd == 'stop':
        print('服务器结束了连接')
        exit()
    elif cmd == 'print':
        print(receiveData(s))
    elif cmd == 'input':
        prompt = receiveData(s)
        string = input(prompt)
        sendData(s, string)
