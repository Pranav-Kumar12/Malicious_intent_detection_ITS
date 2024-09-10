from Crypto.Cipher import AES
import base64
import os

# Planning on doing 128 bit AES key
# Note - pycryto wasn't working ( buffer errors ) so pycrytodome added

class Encryption:
    def __init__(self):
        self.key = os.urandom(16) 

    def pad(self, message):
        padding_needed= (16-len(message) % 16)%16
        message= message + ' '*padding_needed 
        return message
        # Padding messages so that they are multiple of 16



