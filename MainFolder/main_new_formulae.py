import os
import json
import numpy as np
import requests
import math
from datetime import datetime
from RSU_dist_store import update_reputation, reputation_scores
from tempCache.precision import adjustPrecisionErrors

# Folder containing BSM files
folderName = "BSM_Files"
blockchain_url = "http://127.0.0.1:5000"

# Parameters
num_vehicles = 10
g = 0.15  # History parameter for reputation scores
transaction_limit = 100  # Forge a block after 100 transactions
opinion_threshold = 0.5  # Minimum opinion to be eligible as a validator
b= 0.6
l=0.4

# Trust thresholds
speedAvg = 50  # Average speed
receivedPowerAvg = 2.1725113767870305e-6  # Average received power
speedThresholds = [(0.1, 0.9), (0.3, 0.6), (1.0, 0.1)]
powerThresholds = [(0.1, 0.9), (0.3, 0.6), (1.0, 0.1)]
latitudeRange = (37.77, 37.78)
longitudeRange = (-122.42, -122.41)

# Initialize trust matrices
directTrustMatrix = np.zeros((num_vehicles, num_vehicles))
messageCounts = np.zeros((num_vehicles, num_vehicles))
transaction_count = 0

# Calculate parameter trust using thresholds
def calculateParameterTrust(value, avg, thresholds):
    deviation = abs(value - avg) / avg
    for threshold, trustScore in thresholds:
        if deviation <= threshold:
            return trustScore
    return 0  # No trust if beyond max threshold

# Geometric mean calculation
def geometricMean(trustValues):
    product = np.prod(trustValues)
    return product ** (1 / len(trustValues)) if trustValues else 0

# Bayesian updating for comprehensive opinion
def bayesianComprehensiveOpinion(prior, likelihood):
    posterior = (prior * likelihood) / ((prior * likelihood) + ((1 - prior) * (1 - likelihood)))
    return posterior

# Hidden Markov Model-based Reputation Update
def hmm_reputation_update(reputation_scores, comprehensive_opinion, gamma=0.15):
   
    transition_matrix = np.array([
        [1 - gamma, gamma],
        [gamma, 1 - gamma]
    ])
    new_reputation = np.zeros((num_vehicles, 1)) 
    for i in range(num_vehicles):
        current_reputation = np.array([reputation_scores[i, 0], 1 - reputation_scores[i, 0]])
        updated_reputation = np.dot(transition_matrix, current_reputation)
        new_reputation[i,0] = (comprehensive_opinion[i] * updated_reputation[0]) + ((1 - comprehensive_opinion[i]) * updated_reputation[1])
    print("new reputation", new_reputation)
    new_reputation[:] = adjustPrecisionErrors(new_reputation, l)
    print("new reputation", new_reputation)

    for i in range(num_vehicles):
        update_reputation(i, np.clip(new_reputation[i,0], 0.0, 1.0))
    print("Update reputation", update_reputation)


# Direct Trust Calculation
def calculateDirectTrust():
    global directTrustMatrix, messageCounts
    directTrustMatrix = np.zeros((num_vehicles, num_vehicles))
    messageCounts = np.zeros((num_vehicles, num_vehicles))

    for filename in os.listdir(folderName):
        if filename.startswith("bsm") and filename.endswith(".json"):
            parts = filename.replace("bsm", "").replace(".json", "").split("_")
            i, j = int(parts[0]), int(parts[1])

            with open(os.path.join(folderName, filename), "r") as f:
                bsmData = json.load(f)

            speed = bsmData["speed"]
            receivedPower = bsmData.get("receivedPower", 0)
            latitude = bsmData["position"]["latitude"]
            longitude = bsmData["position"]["longitude"]

            speedTrust = calculateParameterTrust(speed, speedAvg, speedThresholds)
            powerTrust = calculateParameterTrust(receivedPower, receivedPowerAvg, powerThresholds)
            latitudeTrust = 0.9 if latitudeRange[0] <= latitude <= latitudeRange[1] else 0.5
            longitudeTrust = 0.9 if longitudeRange[0] <= longitude <= longitudeRange[1] else 0.5

            bsmTrust = geometricMean([speedTrust, powerTrust, latitudeTrust, longitudeTrust])

            directTrustMatrix[i - 1, j - 1] += bsmTrust
            messageCounts[i - 1, j - 1] += 1

    # Average the direct trust matrix
    for i in range(num_vehicles):
        for j in range(num_vehicles):
            if messageCounts[i, j] > 0:
                directTrustMatrix[i, j] /= messageCounts[i, j]

    directTrustMatrix[:] = adjustPrecisionErrors(directTrustMatrix, b)

# Indirect Trust Calculation
def calculateIndirectTrust():
    numVehicles = directTrustMatrix.shape[0]
    indirectTrustMatrix = np.zeros((numVehicles, numVehicles))

    for i in range(numVehicles):
        for j in range(numVehicles):
            if i != j:
                totalTrust = np.sum([directTrustMatrix[k][j] for k in range(numVehicles) if k != i])
                indirectTrustMatrix[i][j] = totalTrust / (numVehicles - 1)

    return indirectTrustMatrix

# Calculate Comprehensive Opinion
def computeComprehensiveEvaluation(directMatrix, indirectMatrix):
    comprehensive_opinion = np.zeros((num_vehicles, num_vehicles))
    for i in range(num_vehicles):
        for j in range(num_vehicles):
            comprehensive_opinion[i, j] = bayesianComprehensiveOpinion(directMatrix[i, j], indirectMatrix[i, j])
    return comprehensive_opinion

# Calculate intermediary opinions
def computeIntermediaryOpinion(comprehensiveEvaluation):
    return np.mean(comprehensiveEvaluation, axis=1)

# Update validators based on reputation
def updateValidators():
    for i in range(num_vehicles):
        opinion = reputation_scores[i, 0]
        if opinion >= opinion_threshold:
            requests.post(f"{blockchain_url}/validator/add", json={"validator_id": f"vehicle_{i + 1}", "opinion_value": opinion})

# Create a time-ordered queue for BSM files
def create_timeQueue():
    timeQueue = []
    for filename in os.listdir(folderName):
        if filename.startswith("bsm") and filename.endswith(".json"):
            with open(os.path.join(folderName, filename), "r") as f:
                bsmData = json.load(f)
                timestamp = datetime.strptime(bsmData["timestamp"], "%Y-%m-%dT%H:%M:%SZ")
                timeQueue.append((timestamp, filename))
    timeQueue.sort(key=lambda x: x[0])
    return timeQueue

# Process BSM files and update trust scores
def process_bsm_files():
    global transaction_count
    timeQueue = create_timeQueue()
    in_val= l
    for timestamp, filename in timeQueue:
        parts = filename.replace("bsm", "").replace(".json", "").split("_")
        sender_vehicle = f"vehicle_{parts[0]}"
        receiver_vehicle = f"vehicle_{parts[1]}"

        with open(os.path.join(folderName, filename), "r") as f:
            bsmData = json.load(f)

        transaction_data = {
            "senderVehicle": sender_vehicle,
            "receiverVehicle": receiver_vehicle,
            "v2xMessage": json.dumps(bsmData)
        }

        response = requests.post(f"{blockchain_url}/transactions/new", json=transaction_data)
        print(f"[{timestamp}] {response.json()}")
        transaction_count += 1

        if transaction_count >= transaction_limit:
            mine_response = requests.get(f"{blockchain_url}/mine")
            print(mine_response.json())

            calculateDirectTrust()
            indirectTrustMatrix = calculateIndirectTrust()
            comprehensiveEvaluation = computeComprehensiveEvaluation(directTrustMatrix, indirectTrustMatrix)
            intermediaryOpinionVector = computeIntermediaryOpinion(comprehensiveEvaluation)
            hmm_reputation_update(reputation_scores, intermediaryOpinionVector, g)
            print("Updated Reputation Scores:")
            print(reputation_scores)
            print('-' * 100)
            updateValidators()
            transaction_count = 0

# Start the process
process_bsm_files()
