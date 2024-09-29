import hashlib
import json
from time import time
from flask import Flask, jsonify, request
from layer1_encryption import Encryption

class Blockchain:
    def __init__(self):
        self.wholeChain= []
        self.currentTransactions= []
        # Have to also later on add genesis block inside init
        self.addBlock(proof=100, previousHash='0000') 
        # genesis block doesn't need to have proper proof of work and previous_hash. Any random value here should work.
        self.encryption = Encryption()  # Encryption instance for use in blockchain
        self.opinion = 0.5 # new block in sub-net/group has opinion value 0

    def addBlock(self, proof, previousHash= None):
        # proof is based on proof of work algorithm

        curBlock= {
            'index': len(self.wholeChain)+ 1, # 1 based
            'timestamp': time(), 
            'transactions': self.currentTransactions,
            'proof': proof,
            'previousHash': previousHash or self.getHash(self.wholeChain[-1])
        }
        # all the transactions will be put in this block so reset all 
        self.currentTransactions= []
        self.wholeChain.append(curBlock)
        return curBlock

    # Each new V2X message is being made a part of a new transaction in blockchain

    def newMessage(self, senderVehicle, receiverVehicle, v2xMessage):
        encryptedV2xMessage = self.encryption.encrypt(v2xMessage).decode('utf-8')  # Encrypt the message
        newMessageTransaction= {
            'senderVehicle': senderVehicle,
            'receiverVehicle': receiverVehicle,
            'v2xMessage': encryptedV2xMessage 
        }

        self.currentTransactions.append(newMessageTransaction)

        # Returning the block to which it belongs i.e. last block index +1 ( part of new mined block )
        return self.wholeChain[-1]['index']+ 1
    
    def decryptMessage(self, encrypted_message):
        decrypted_message = self.encryption.decrypt(encrypted_message.encode('utf-8'))
        return decrypted_message
    

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
        if(len(hashUnderReview)>=4 and hashUnderReview[0]=='0' and hashUnderReview[1]=='0' and hashUnderReview[2]=='0' and hashUnderReview[3]=='0'):    return True
        return False


    def proofOfWork(self, previousProof):
        # have to find curProof such that hash(curProof*previousProof) has 4 leading zeroes = famous riddle to solve
        # This proof of work makes it so computationally expensive to forge a new block so it necessry makes blockchain immutable
        curProof= 0
        while True:
            result= self.validateProof(previousProof, curProof)
            if(result):  break
            else: curProof+=1
        return curProof
    

app= Flask(__name__)

blockchain= Blockchain()

@app.route('/transactions/new', methods= ['POST'])
def newTransaction():
    data= request.get_json()

    # checking missing fields
    fieldsNeeded= ['senderVehicle', 'receiverVehicle', 'v2xMessage']
    for field in fieldsNeeded:
        isMissing= True
        for fieldPresent in data:
            if(field==fieldPresent):
                isMissing= False
        if(isMissing):
            return 'Missing fields in transaction', 400

    indexObtained= blockchain.newMessage(data['senderVehicle'], data['receiverVehicle'], data['v2xMessage'])

    response= {'message' : f'New message transaction for block number {indexObtained}'}

    return jsonify(response), 201

# this API end point is supposed to be helping nodes decrypt immutable transaction present on blockchain
@app.route('/transactions/decrypt', methods=['POST'])
def decrypt_transaction():
    data= request.get_json()
    # Going to that particular block index and transaction index to find the encrypted message and then decrypt it
    blockIndex= data.get('blockIndex', None)
    transactionIndex= data.get('transactionIndex', None)
    if blockIndex is None or transactionIndex is None:
        return 'Either block index or transaction index is missing', 400

    # both are 1 based indexes
    if blockIndex<1 or blockIndex>len(blockchain.wholeChain):
        return 'Block index is invalid', 400

    block= blockchain.wholeChain[blockIndex-1]
    if transactionIndex<1 or transactionIndex>len(block['transactions']):
        return 'Transaction index is invalid', 400

    encryptedMessage = block['transactions'][transactionIndex - 1]['v2xMessage']
    decryptedMessage = blockchain.decryptMessage(encryptedMessage)
    response = {'decryptedMessage': decryptedMessage}
    return jsonify(response), 200


@app.route('/mine', methods=['GET'])
def mineBlock():
    # Anybody in the network can mine this block and add to blockchain- consensus over distributed network
    # Mining a new block to be added to wholeChain
    # Proof of work algorithm will be executed and new block forged to the chain
    lastBlock= blockchain.wholeChain[-1]
    lastBlockProof= lastBlock['proof']
    curProof= blockchain.proofOfWork(lastBlockProof)

    previousHash= blockchain.getHash(lastBlock)
    curBlock= blockchain.addBlock(curProof, previousHash)

    response= {
        'message': 'New block mined',
        'transactions': curBlock['transactions'],
        'proof': curBlock['proof'],
        'previousHash': curBlock['previousHash'],
        'index': curBlock['index'],
        'timestamp': curBlock['timestamp']
    }

    return jsonify(response), 200

@app.route('/chain', methods= ['GET'])
def whole_chain():
    # whole chain and length
    response= {
        'chain': blockchain.wholeChain,
        'chainLength': len(blockchain.wholeChain)
    } 

    return jsonify(response), 200

"""
Now an api end point that combines all multi hierarchial level of encryption, adversarially robust network and ledger will be added
Called as handleV2xMessage
When a message is captured after being broadcasted to nearby vehicles then handling these messages will be in this
Can have cross network communications, broadcast transaction pool etc. but it will mostly be handled one by one.

"""


if __name__ == '__main__':
    app.run(host='0.0.0.0', port= 5050)