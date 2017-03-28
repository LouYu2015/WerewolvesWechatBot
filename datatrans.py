'''
Author: Yu Lou(louyu27@gmail.com)

Send strings between machines over socket.
'''
import struct

def sendData(sock, data):
    '''
    Send string through socket.
    '''
    encoded = data.encode('utf-8')
    sock.send(struct.pack('Q', len(encoded)))
    sock.send(encoded)
    
def receiveData(sock):
    '''
    Receive object through socket.
    '''
    lengthLeft = struct.unpack('Q', sock.recv(struct.calcsize('Q')))[0]
    data = bytes()
    while lengthLeft > 0:
        block = sock.recv(lengthLeft)
        data += block
        lengthLeft -= len(block)
    return data.decode('utf-8')
