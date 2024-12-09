from functools import reduce
import hashlib
import random
import requests
import json
from time import time
from flask import Flask, jsonify, request
from layer1Encryption import Encryption
import os
import math
import numpy as np
from RSU_dist_store import update_reputation, reputation_scores
from tempCache.precision import adjustPrecisionErrors
folderName = "BSM_Files"
blockchain_url = "http://127.0.0.1:5000"

speedAvg = 50  # average speed
receivedPowerAvg = 2.1725113767870305e-6  # average received power
speedThresholds = [(0.1, 0.9), (0.3, 0.6), (1.0, 0.1)]  # threshold ratio, trust score for speed
powerThresholds = [(0.1, 0.9), (0.3, 0.6), (1.0, 0.1)]  # threshold ratio, trust score for received power
latitudeRange = (37.77, 37.78)  # latitude range
longitudeRange = (-122.42, -122.41)  # longitude range

def calculateParameterTrust(value, avg, thresholds):
    deviation = abs(value - avg) / avg
    for threshold, trustScore in thresholds:
        if deviation <= threshold:
            return trustScore
    return 0  # No trust if beyond max threshold

def geometricMean(trustValues):
    product = math.prod(trustValues)
    return product ** (1 / len(trustValues)) if trustValues else 0

directTrustMatrix = np.zeros((10, 10))
messageCounts = np.zeros((10, 10))
# We will be needing both because there can be multiple direct trust valuations for vehicle i from vehicle j as it can receive multiple bsm
# So will average out them.

for filename in os.listdir(folderName):
    if filename.startswith("bsm") and filename.endswith(".json"):
        parts = filename.replace("bsm", "").replace(".json", "").split("_")
        i, j = int(parts[0]), int(parts[1])
        
        with open(os.path.join(folderName, filename), "r") as f:
            bsmData = json.load(f)
        
        speed = bsmData["speed"]
        receivedPower = bsmData.get("receivedPower", 0)  # Assuming receivedPower is already part of the BSM data
        latitude = bsmData["position"]["latitude"]
        longitude = bsmData["position"]["longitude"]
        
        # Calculate trust for speed
        speedTrust = calculateParameterTrust(speed, speedAvg, speedThresholds)
        
        # Calculate trust for received power
        powerTrust = calculateParameterTrust(receivedPower, receivedPowerAvg, powerThresholds)
        
        # Calculate trust for latitude and longitude
        latitudeTrust = 0.9 if latitudeRange[0] <= latitude <= latitudeRange[1] else 0.5
        longitudeTrust = 0.9 if longitudeRange[0] <= longitude <= longitudeRange[1] else 0.5
        
        # Compute the BSM trust using the geometric mean of the trusts
        bsmTrust = geometricMean([speedTrust, powerTrust, latitudeTrust, longitudeTrust])
        
        directTrustMatrix[i-1, j-1] += bsmTrust 
        messageCounts[i-1, j-1] += 1

# Average out the direct trust matrix by dividing by the message counts
for i in range(10):
    for j in range(10):
        if messageCounts[i, j] > 0:
            directTrustMatrix[i, j] /= messageCounts[i, j]

directTrustMatrix= adjustPrecisionErrors(directTrustMatrix)
# Print the final direct trust matrix
print("Direct Trust Matrix:")
print(directTrustMatrix)
print()
print('-'*100)
print()

def calculateIndirectTrust(directTrustMatrix):
    numVehicles = directTrustMatrix.shape[0]
    indirectTrustMatrix = np.zeros((numVehicles, numVehicles))

    for i in range(numVehicles):      # For each vehicle i
        for j in range(numVehicles):  # For each vehicle j
            if i != j:
                totalTrust = np.sum([directTrustMatrix[k][j] for k in range(numVehicles) if k != i])
                indirectTrustMatrix[i][j] = totalTrust / (numVehicles - 1)
    
    return indirectTrustMatrix

# Example Usage
indirectTrustMatrix = calculateIndirectTrust(directTrustMatrix)
print("Indirect Trust Matrix:")
print(indirectTrustMatrix)
print()
print('-'*100)
print()

def computeComprehensiveEvaluation(directMatrix, indirectMatrix, weight_direct=0.68, weight_indirect=0.32):
    comprehensiveEvaluation = weight_direct * directMatrix + weight_indirect * indirectMatrix
    return comprehensiveEvaluation

comprehensiveEvaluation = computeComprehensiveEvaluation(directTrustMatrix, indirectTrustMatrix)
print("Comprehensive Trust Matrix:")
print(comprehensiveEvaluation)
print()
print('-'*100)
print()

def computeIntermediaryOpinion(comprehensiveEvaluation):
    intermediaryOpinionVector = np.mean(comprehensiveEvaluation, axis=1)
    return intermediaryOpinionVector

intermediaryOpinionVector = computeIntermediaryOpinion(comprehensiveEvaluation)
print("Intermediary Opinion Vector:")
print(intermediaryOpinionVector)
print()
print('-'*100)
print()


g= 0.15 #  history parameter
num_vehicles = 10 

def update_reputation_scores(intermediary_opinion, reputation_scores, g):
    # Calculate the current reputation score and update the reputation matrix
    for i in range(num_vehicles):
        reputationScoreCur = intermediary_opinion[i] + g * reputation_scores[i, 0] + g**2 * reputation_scores[i, 1] + g**3 * reputation_scores[i, 2]
        update_reputation(i, reputationScoreCur)

update_reputation_scores(intermediaryOpinionVector, reputation_scores, g)

print("Reputation scores : ")
print(reputation_scores)

print()
print('-'*100)
print()


class Blockchain:
    def __init__(self):
        self.wholeChain = []
        self.currentTransactions = []
        self.encryption = Encryption()
        self.validators = {}
        self.opinion = 0.5
        self.threshold = 0.5
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

@app.route('/', methods= ['GET'])
def start():
    response = {
        'message': 'Starter page'
    }
    return 'Home page', 200

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
