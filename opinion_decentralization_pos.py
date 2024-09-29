from functools import reduce
import hashlib
import random
import json
from time import time
from flask import Flask, jsonify, request
from layer1_encryption import Encryption

class Blockchain:
    def __init__(self):
        self.wholeChain = []
        self.currentTransactions = []
        self.encryption = Encryption()
        self.validators = {}
        self.opinion = 0.5
        self.threshold = 0.3
        self.addBlock(validatorId='genesisValidator', previousHash='0000')

    def addValidator(self, validatorId, opinionValue=0.5):
        self.validators[validatorId] = opinionValue

    def calculateDirectOpinion(self, directParams):
        if directParams:
            directOpinion = (reduce(lambda x, y: x * y, directParams)) ** (1 / len(directParams))
        else:
            directOpinion = 0
        return directOpinion

    def delegateOpinion(self, validatorId, stakeValue):
        if validatorId in self.validators:
            if self.validators[validatorId] >= stakeValue:
                self.validators[validatorId] -= stakeValue
                return stakeValue
            else:
                return 0
        else:
            raise ValueError("Validator not found in network.")

    def selectValidator(self):
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

    def isTransactionUnique(self, newTransaction):
        for transaction in self.currentTransactions:
            if transaction['senderVehicle'] == newTransaction['senderVehicle'] and transaction['v2xMessage'] == newTransaction['v2xMessage']:
                return False
        return True

    def addBlock(self, validatorId, previousHash=None):
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

    def proofOfStake(self, validatorId, stakeValue):
        stakedOpinion = self.delegateOpinion(validatorId, stakeValue)
        if stakedOpinion == 0:
            return None
        return stakedOpinion

    def verifyBlock(self, validatorId, stakeValue=0.1):
        lastBlock = self.wholeChain[-1]
        previousHash = self.getHash(lastBlock)
        stakedValue = self.proofOfStake(validatorId, stakeValue)

        if stakedValue:
            curBlock = self.addBlock(validatorId, previousHash)
            self.validators[validatorId] += 0.1
            return curBlock
        else:
            return None

    def newMessage(self, senderVehicle, receiverVehicle, v2xMessage):
        encryptedV2xMessage = self.encryption.encrypt(v2xMessage).decode('utf-8')
        newMessageTransaction = {
            'senderVehicle': senderVehicle,
            'receiverVehicle': receiverVehicle,
            'v2xMessage': encryptedV2xMessage
        }

        if self.isTransactionUnique(newMessageTransaction):
            self.currentTransactions.append(newMessageTransaction)
            return self.wholeChain[-1]['index'] + 1
        else:
            raise ValueError("Duplicate transaction detected.")

    def decryptMessage(self, encryptedMessage):
        decryptedMessage = self.encryption.decrypt(encryptedMessage.encode('utf-8'))
        return decryptedMessage

    def getHash(self, block):
        blockString = json.dumps(block, sort_keys=True)
        encodedBlockString = blockString.encode()
        hashedCode = hashlib.sha256(encodedBlockString)
        return hashedCode.hexdigest()

app = Flask(__name__)

blockchain = Blockchain()

@app.route('/transactions/new', methods=['POST'])
def newTransaction():
    data = request.get_json()
    fieldsNeeded = ['senderVehicle', 'receiverVehicle', 'v2xMessage']
    for field in fieldsNeeded:
        if field not in data:
            return 'Missing fields in transaction', 400

    try:
        indexObtained = blockchain.newMessage(data['senderVehicle'], data['receiverVehicle'], data['v2xMessage'])
        response = {'message': f'New message transaction for block number {indexObtained}'}
        return jsonify(response), 201
    except ValueError as e:
        return str(e), 400

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

@app.route('/mine', methods=['GET'])
def mineBlock():
    try:
        selectedValidator = blockchain.selectValidator()
        newBlock = blockchain.verifyBlock(selectedValidator)

        if newBlock:
            response = {
                'message': f'Block successfully mined by Validator {selectedValidator}',
                'block': newBlock,
            }
        else:
            response = {
                'message': f'Block mining failed by Validator {selectedValidator}',
            }

    except ValueError as e:
        response = {'message': str(e)}

    return jsonify(response), 200

@app.route('/validator/add', methods=['POST'])
def addValidator():
    data = request.get_json()
    validatorId = data.get('validator_id', None)

    if validatorId:
        blockchain.addValidator(validatorId)
        response = {'message': f'Validator {validatorId} added with initial opinion value'}
        return jsonify(response), 201
    else:
        return 'Validator ID missing', 400

@app.route('/validator/stake', methods=['POST'])
def stakeOpinion():
    data = request.get_json()
    validatorId = data.get('validator_id', None)
    stakeValue = data.get('stake_value', None)

    if validatorId and stakeValue:
        stakedValue = blockchain.delegateOpinion(validatorId, float(stakeValue))
        if stakedValue > 0:
            response = {'message': f'Validator {validatorId} staked {stakeValue} opinion points'}
        else:
            response = {'message': f'Validator {validatorId} not enough opinion to stake'}
    else:
        return 'Validator ID or stake value missing', 400

    return jsonify(response), 200

@app.route('/chain', methods= ['GET'])
def whole_chain():
    # whole chain and length
    response= {
        'chain': blockchain.wholeChain,
        'chainLength': len(blockchain.wholeChain)
    } 

    return jsonify(response), 200

if __name__ == '__main__':
    app.run(debug=True)
