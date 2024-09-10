from Crypto.Cipher import AES
import base64
import os
import json

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


    # encryption and decryption code 


    def encrypt(self, message):
        message = self.pad(message)
        #Padding before encrypting
        cipher = AES.new(self.key, AES.MODE_ECB)
        encrypted_message = base64.b64encode(cipher.encrypt(message.encode('utf-8')))
        # Following utf-8 as of now
        return encrypted_message

    def decrypt(self, encrypted_message):
        cipher = AES.new(self.key, AES.MODE_ECB)
        decrypted_message = cipher.decrypt(base64.b64decode(encrypted_message)).decode('utf-8').rstrip()
        return decrypted_message

    

with open('bsm.json','r') as file:
    data= json.load(file)  
    # data becomes python object loading json data

json_string = json.dumps(data)
# This is stringify method as called in javascript

encryption = Encryption()
encrypted_message = encryption.encrypt(json_string)

print("Encrypted message is -> ", encrypted_message)
print()

decrypted_message = encryption.decrypt(encrypted_message)

print("Decrypted message is -> ", decrypted_message)