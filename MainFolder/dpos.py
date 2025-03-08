import hashlib
import random
import json
from time import time
from datetime import datetime
from flask import Flask, jsonify, request
from layer1Encryption import Encryption
from RSU_dist_store import reputation_scores

def getTrasactionId(sender, receiver):
    timeNow = time()
    transactionID = f"{sender[8::]}.{timeNow}.{receiver[8::]}"
    return transactionID

class Blockchain:
    def __init__(self):
        self.wholeChain = []
        self.currentTransactions = []
        self.encryption = Encryption()
        self.validators = {}
        self.addBlock(validatorId='genesisValidator', previousHash='0000')

    def decryptMessage(self, encryptedMessage):
        decryptedMessage = self.encryption.decrypt(encryptedMessage.encode('utf-8'))
        return decryptedMessage
    
    def addValidator(self, validatorId, opinionValue):
        """Add a validator with an initial opinion value."""
        self.validators[validatorId] = opinionValue

    def selectValidator(self):
        """Select a validator based on their opinion values."""
        totalOpinion = sum(self.validators.values())
        if totalOpinion == 0:
            raise ValueError("No validators with positive opinion available.")

        randomChoice = random.uniform(0, totalOpinion)
        cumulative = 0
        for validator, opinion in self.validators.items():
            cumulative += opinion
            if cumulative > randomChoice:
                return validator
        return None

    def addBlock(self, validatorId, previousHash=None):
        """Add a block to the blockchain."""
        curBlock = {
            'index': len(self.wholeChain) + 1,
            'timestamp': time(),
            'transactions': self.currentTransactions,
            'validator': validatorId,
            'previousHash': previousHash or self.getHash(self.wholeChain[-1])
        }
        self.currentTransactions = []
        self.wholeChain.append(curBlock)
        return curBlock

    def getHash(self, block):
        """Generate the SHA-256 hash of a block."""
        blockString = json.dumps(block, sort_keys=True)
        return hashlib.sha256(blockString.encode()).hexdigest()

    def newMessage(self, senderVehicle, receiverVehicle, v2xMessage):
        """Add a new transaction to the current transactions list."""
        encryptedV2xMessage = self.encryption.encrypt(v2xMessage).decode('utf-8')
        newMessageTransaction = {
            'senderVehicle': senderVehicle,
            'receiverVehicle': receiverVehicle,
            'transactionId': getTrasactionId(senderVehicle, receiverVehicle),
            'v2xMessage': encryptedV2xMessage,
            'validationStatus': 'trusted',
            'RSU_ID': 'rsu1'
        }
        self.currentTransactions.append(newMessageTransaction)
        return self.wholeChain[-1]['index'] + 1

    def verifyAndAddBlock(self):
        """Select a validator and attempt to forge a block."""
        try:
            selectedValidator = self.selectValidator()
            newBlock = self.addBlock(selectedValidator)
            return newBlock, f"Block successfully forged by validator {selectedValidator}"
        except ValueError as e:
            return None, str(e)


# Initialize Flask app
app = Flask(__name__)
blockchain = Blockchain()

@app.route('/transactions/new', methods=['POST'])
def newTransaction():
    data = request.get_json()
    required_fields = ['senderVehicle', 'receiverVehicle', 'v2xMessage']

    if not all(field in data for field in required_fields):
        return "Missing fields in transaction", 400

    index = blockchain.newMessage(data['senderVehicle'], data['receiverVehicle'], data['v2xMessage'])
    return jsonify({'message': f'New transaction added to block {index}'}), 201

@app.route('/mine', methods=['GET'])
def mineBlock():
    newBlock, message = blockchain.verifyAndAddBlock()
    if newBlock:
        response = {'message': message, 'block': newBlock}
    else:
        response = {'message': message}
    return jsonify(response), 200

@app.route('/transactions/decrypt', methods=['POST'])
def decryptTransaction():
    data = request.get_json()

    blockIndex = data.get('blockIndex', None)
    transactionIndex = data.get('transactionIndex', None)

    if blockIndex is None or transactionIndex is None:
        return 'Either block index or transaction index is missing', 400

    if blockIndex < 1 or blockIndex > len(blockchain.wholeChain):
        return 'Block index is invalid', 400

    block = blockchain.wholeChain[blockIndex - 1]
    if transactionIndex < 1 or transactionIndex > len(block['transactions']):
        return 'Transaction index is invalid', 400

    encryptedMessage = block['transactions'][transactionIndex - 1]['v2xMessage']
    decryptedMessage = blockchain.decryptMessage(encryptedMessage)
    response = {'decryptedMessage': decryptedMessage}
    return jsonify(response), 200

@app.route('/chain', methods=['GET'])
def whole_chain():
    return jsonify({'consensusType': 'DPos','chain': blockchain.wholeChain, 'length': len(blockchain.wholeChain)}), 200

if __name__ == '__main__':
    for i in range(10):
        blockchain.addValidator(f"vehicle_{i + 1}", reputation_scores[i, 0])
    app.run(debug=True)
