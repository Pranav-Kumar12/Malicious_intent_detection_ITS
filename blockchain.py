import hashlib
import json
from time import time
from flask import Flask, jsonify, request
import layer1_encryption

class Blockchain:
    def __init__(self):
        self.wholeChain= []
        self.currentTransactions= []
        # Have to also later on add genesis block inside init
        self.addBlock(proof=100, previousHash='0000') 
        # genesis block doesn't need to have proper proof of work and previous_hash. Any random value here should work.

    def addBlock(self, proof, previousHash= None):
        # proof is based on proof of work algorithm

        curBlock= {
            'index': len(self.wholeChain)+ 1, # 1 based
            'timestamp': time(), 
            'transactions': self.currentTransactions,
            'proof': proof,
            'previousHash': previousHash
        }
        # all the transactions will be put in this block so reset all 
        self.currentTransactions= []
        self.wholeChain.append(curBlock)
        return curBlock

    # Each new V2X message is being made a part of a new transaction in blockchain

    def newMessage(self, senderVehicle, receiverVehicle, v2xMessage):
        newMessageTransaction= {
            'senderVehicle': senderVehicle,
            'receiverVehicle': receiverVehicle,
            'v2xMessage': v2xMessage 
        }

        self.currentTransactions.append(newMessageTransaction)

        # Returning the block to which it belongs i.e. last block index +1 ( part of new mined block )
        return self.wholeChain[-1]['index']+ 1
    

    def getHash(block):
        # SHA-256 hash based
        # Block needs to be stringified and sorted based on keys of json object to ensure uniform hashing
        # encodes converts to binary bits for hashing

        blockString= json.dumps(block, sort_keys= True)
        encodedBlockString= blockString.encode()
        hashedCode= hashlib.sha256(encodedBlockString)
        return hashedCode.hexdigest() # better readability and storage in hexadecimal
    

# """

# Have to add proof of work working and then there will be api points exposed for application and mining.

# """

    def validateProof(previousProof, curProof):
        # simple check if hash(curProof, proof) contains leading 4 zeroes or not
        mergeProofs= f'{previousProof}{curProof}'
        mergeProofs= mergeProofs.encode()
        hashUnderReview= hashlib.sha256(mergeProofs).hexdigest()
        if(len(hashUnderReview)>=4 and hashUnderReview[0]=='0' and hashUnderReview[1]=='0' and hashUnderReview[2]=='0' and hashUnderReview[3]=='0'){
            return True
        }
        return False


    def proofOfWork(self, previousProof):
        # have to find curProof such that hash(curProof*previousProof) has 4 leading zeroes = famous riddle to solve

        curProof= 0
        while True:
            result= self.validateProof(previousProof, curProof)
            if(result):  break
            else: curProof+=1
        return curProof