import base64

def base64_encode(to_encode: str):
    return base64.b64encode(to_encode.encode('utf-8'))

def base64_decode(encoded):
    return base64.b64decode(encoded).decode('utf-8')