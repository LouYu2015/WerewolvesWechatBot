'''
Author: Yu Lou(louyu27@gmail.com)

Send strings between machines over socket.
'''
import struct

def sendData(sock, data):
    '''
    Send string through socket.
    '''
    sock.send(struct.pack('Q', len(data)))
    sock.send(data)
    
def receiveData(sock):
    '''
    Receive object through socket.
    '''
    lengthLeft = struct.unpack('Q', sock.recv(struct.calcsize('Q')))[0]
    data = ''
    while lengthLeft > 0:
        block = sock.recv(lengthLeft)
        data += block
        lengthLeft -= len(block)
    return data
