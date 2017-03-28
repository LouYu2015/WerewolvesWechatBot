# -*- coding: UTF-8 -*-
'''
Author: Yu Lou(louyu27@gmail.com)

Client side program for Werewolf game, running on Python 2.7.
'''
import socket
import struct
import sys, locale

def sendData(sock, data):
    '''
    Send string through socket.
    '''
    sock.send(struct.pack('Q', len(data)))
    sock.send(data)
    
def receiveData(sock):
    '''
    Receive object through socket by unpickling it.
    '''
    lengthLeft = struct.unpack('Q', sock.recv(struct.calcsize('Q')))[0]
    data = ''
    while lengthLeft > 0:
        block = sock.recv(lengthLeft)
        data += block
        lengthLeft -= len(block)
    return data

while True:
    try:
        ip = raw_input('输入服务器地址:')
        port = int(raw_input('输入服务器端口:'))

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
        string = raw_input(prompt).decode(sys.stdin.encoding or locale.getpreferredencoding(True)).encode('utf-8')
        sendData(s, string)
