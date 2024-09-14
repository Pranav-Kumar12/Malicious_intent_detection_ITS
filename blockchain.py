import hashlib
import json
from time import time
from flask import Flask, jsonify, request
import layer1_encryption

class Blockchain:
    def __init__(self):
        self.whole_chain= []
        self.current_transactions= []
        # Have to also later on add genesis block inside init
        self.add_block(proof=100, previous_hash='0000') 
        # genesis block doesn't need to have proper proof of work and previous_hash. Any random value here should work.

    def add_block(self, proof, previous_hash= None):
        # proof is based on proof of work algorithm

        cur_block= {
            'index': len(self.whole_chain)+ 1, # 1 based
            'timestamp': time(), 
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash
        }
        # all the transactions will be put in this block so reset all 
        self.current_transactions= []
        self.whole_chain.append(cur_block)
        return cur_block

    # Each new V2X message is being made a part of a new transaction in blockchain

    def new_message(self, senderVehicle, receiverVehicle, v2xMessage):
        new_message_transaction= {
            'senderVehicle': senderVehicle,
            'receiverVehicle': receiverVehicle,
            'v2xMessage': v2xMessage 
        }

        self.current_transactions.append(new_message_transaction)

        # Returning the block to which it belongs i.e. last block index +1 ( part of new mined block )
        return self.whole_chain[-1]['index']+ 1