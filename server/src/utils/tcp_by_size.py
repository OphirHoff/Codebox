"""
TCP message handling utilities with size-prefixed protocol implementation.

This module provides two different implementations for sending and receiving TCP messages:
1. Simple size-prefixed protocol (8-byte header)
2. Binary size-prefixed protocol (4-byte header, network byte order)

The size-prefixed protocols ensure complete message transmission by sending the message size
before the actual data. This prevents message boundaries from becoming mixed up.

Constants:
    size_header_size (int): Size of the header for the simple protocol (8 bytes)
    TCP_DEBUG (bool): Enable/disable debug logging of TCP operations
"""

import socket,struct
import logging

size_header_size = 8
TCP_DEBUG = False

def __log(prefix, data, max_to_print=100):
    """
    Internal debug logging function for TCP operations.

    Args:
        prefix: Message prefix for the log
        data: Data to be logged
        max_to_print: Maximum number of bytes to print (default: 100)
    """
    if not TCP_DEBUG:
        return
    data_to_log = data[:max_to_print]
    if type(data_to_log) == bytes:
        try:
            data_to_log = data_to_log.decode()
        except (UnicodeDecodeError, AttributeError):
            pass
    # print(f"\n{prefix}({len(data)})>>>{data_to_log}")
    logging.info(f"\n{prefix}({len(data)})>>>{data_to_log}")


def __recv_amount(sock, size=4):
    """
    Internal function to receive exact amount of bytes from socket.

    Args:
        sock: Socket to receive from
        size: Number of bytes to receive (default: 4)

    Returns:
        bytes: Received data or empty bytes if connection closed
    """
    buffer = b''
    while size:
        new_bufffer = sock.recv(size)
        if not new_bufffer:
            return b''
        buffer += new_bufffer
        size -= len(new_bufffer)
    return buffer 


def recv_by_size(sock, return_type="string"):
    """
    Receive a message using simple size-prefixed protocol (8-byte header).

    Args:
        sock: Socket to receive from
        return_type: Type of returned data ("string" or "bytes")

    Returns:
        str or bytes: Received message in specified format
    """
    try:
        data  = b''
        data_len = int(__recv_amount(sock, size_header_size))
        # code handle the case of data_len 0
        data = __recv_amount(sock, data_len)
        __log("Receive", data)
        if return_type == "string":
            return data.decode()
    except OSError:
        data = '' if return_type=="string" else b''
    return data


def send_with_size(sock, data):
    """
    Send a message using simple size-prefixed protocol (8-byte header).

    Args:
        sock: Socket to send through
        data: Data to send (string or bytes)
    """
    if len(data) == 0:
        return
    try:
        if type(data) != bytes:
            data = data.encode()
        len_data = str(len(data)).zfill(size_header_size).encode()
        data = len_data + data
        sock.sendall(data)
        __log("Sent", data)
    except Exception as err:
        print("ERROR : " + str(err))
    # except OSError:
    #     print('ERROR: send_with_size with except OSError')


def __hex(s):
    """
    Internal debug function to print hexadecimal representation of string.

    Args:
        s: String to convert to hex display
    """
    cnt = 0
    for i in range(len(s)):
        if cnt % 16 == 0:
            print ("")
        elif cnt % 8 ==0:
            print ("    ",end='')
        cnt +=1
        print ("%02X" % int(ord(s[i])),end='')


"""
#
Binary Size by 4 bytes   from 1 to 4GB
#
"""
def send_one_message(sock, data):
    """
    Send a message using binary size-prefixed protocol (4-byte header).
    
    Uses network byte order for size header.

    Args:
        sock: Socket to send through
        data: Data to send (string or bytes)
    """
    #sock.sendall(struct.pack('!I', len(message)) + message)
    try:
        length = socket.htonl(len(data))
        if type(data) != bytes:
            data = data.encode()
        sock.sendall(struct.pack('I', length) + data)
        data_part = data[:100]
        if TCP_DEBUG  and len(data) > 0:
            print(f"\nSent({len(data)})>>>{data_part}")
    except:
        print(f"ERROR in send_one_message")
   

def recv_one_message(sock, return_type="string"):
    """
    Receive a message using binary size-prefixed protocol (4-byte header).
    
    Uses network byte order for size header.

    Args:
        sock: Socket to receive from
        return_type: Type of returned data ("string" or "bytes")

    Returns:
        str or bytes: Received message in specified format, None if connection closed
    """
    len_section = __recv_amount(sock, 4)
    if not len_section:
        return None
    len_int, = struct.unpack('I', len_section)
    len_int = socket.ntohl(len_int)
    
    data =  __recv_amount(sock, len_int)
    if TCP_DEBUG and len(data) != 0:
        print(f"\nRecv({len_int})>>>{data[:100]}")

    if len_int != len(data):
        data=b'' # Partial data is like no data !
    if return_type == "string":
        return data.decode()
      
    return data
