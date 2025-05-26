"""
Async TCP message handling utilities with size-prefixed protocol implementation.

This module provides an async implementation for sending and receiving TCP messages
using a binary size-prefixed protocol (4-byte header, network byte order).

The size-prefixed protocol ensures complete message transmission by sending the message size
before the actual data. This prevents message boundaries from becoming mixed up.

Constants:
    TCP_DEBUG (bool): Enable/disable debug logging of TCP operations
"""

import struct
import socket
import logging
import asyncio

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
    if isinstance(data_to_log, bytes):
        try:
            data_to_log = data_to_log.decode()
        except (UnicodeDecodeError, AttributeError):
            pass
    logging.info(f"\n{prefix}({len(data)})>>>{data_to_log}")

async def __recv_amount(reader: asyncio.StreamReader, size: int) -> bytes:
    """
    Internal async function to receive exact amount of bytes from stream.

    Args:
        reader: StreamReader to receive from
        size: Number of bytes to receive

    Returns:
        bytes: Received data or empty bytes if connection closed
    """
    buffer = b''
    remaining = size
    while remaining:
        chunk = await reader.read(remaining)
        if not chunk:  # EOF
            return b''
        buffer += chunk
        remaining -= len(chunk)
    return buffer

async def send_one_message(writer: asyncio.StreamWriter, data):
    """
    Send a message using binary size-prefixed protocol (4-byte header).
    
    Uses network byte order for size header.

    Args:
        writer: StreamWriter to send through
        data: Data to send (string or bytes)
    """
    try:
        if not isinstance(data, bytes):
            data = data.encode()
        
        length = socket.htonl(len(data))
        writer.write(struct.pack('I', length) + data)
        await writer.drain()
        
        if TCP_DEBUG and data:
            print(f"\nSent({len(data)})>>>{data[:100]}")
    except Exception as e:
        logging.error(f"Error in send_one_message: {e}")

async def recv_one_message(reader: asyncio.StreamReader, return_type="string"):
    """
    Receive a message using binary size-prefixed protocol (4-byte header).
    
    Uses network byte order for size header.

    Args:
        reader: StreamReader to receive from
        return_type: Type of returned data ("string" or "bytes")

    Returns:
        str or bytes: Received message in specified format, None if connection closed
    """
    try:
        # Read the 4-byte length header
        len_section = await __recv_amount(reader, 4)
        if not len_section:
            return None

        # Unpack the length (network byte order)
        len_int, = struct.unpack('I', len_section)
        len_int = socket.ntohl(len_int)

        # Read the actual data
        data = await __recv_amount(reader, len_int)
        
        if TCP_DEBUG and data:
            print(f"\nRecv({len_int})>>>{data[:100]}")

        # Verify we got all the data
        if len_int != len(data):
            return None if return_type == "string" else b''

        # Return in requested format
        if return_type == "string":
            return data.decode()
        return data

    except Exception as e:
        logging.error(f"Error in recv_one_message: {e}")
        return None if return_type == "string" else b'' 