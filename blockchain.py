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
