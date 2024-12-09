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


def calculateParameterTrust(value, avg, thresholds):
    deviation = abs(value - avg) / avg
    for threshold, trustScore in thresholds:
        if deviation <= threshold:
            return trustScore
    return 0  # No trust if beyond max threshold


def geometricMean(trustValues):
    product = np.prod(trustValues)
    return product ** (1 / len(trustValues)) if trustValues else 0


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

    directTrustMatrix[:] = adjustPrecisionErrors(directTrustMatrix)


def calculateIndirectTrust():
    numVehicles = directTrustMatrix.shape[0]
    indirectTrustMatrix = np.zeros((numVehicles, numVehicles))

    for i in range(numVehicles):
        for j in range(numVehicles):
            if i != j:
                totalTrust = np.sum([directTrustMatrix[k][j] for k in range(numVehicles) if k != i])
                indirectTrustMatrix[i][j] = totalTrust / (numVehicles - 1)

    return indirectTrustMatrix


def computeComprehensiveEvaluation(directMatrix, indirectMatrix, weight_direct=0.68, weight_indirect=0.32):
    return weight_direct * directMatrix + weight_indirect * indirectMatrix


def computeIntermediaryOpinion(comprehensiveEvaluation):
    return np.mean(comprehensiveEvaluation, axis=1)

g= 0.15 #  history parameter
num_vehicles = 10 

def update_reputation_scores(intermediary_opinion, reputation_scores, g):
    # Calculate the current reputation score and update the reputation matrix
    for i in range(num_vehicles):
        reputationScoreCur = intermediary_opinion[i] + g * reputation_scores[i, 0] + g**2 * reputation_scores[i, 1] + g**3 * reputation_scores[i, 2]
        update_reputation(i, reputationScoreCur)

def updateValidators():
    for i in range(num_vehicles):
        opinion = reputation_scores[i, 0]
        if opinion >= opinion_threshold:
            requests.post(f"{blockchain_url}/validator/add", json={"validator_id": f"vehicle_{i + 1}", "opinion_value": opinion})


def create_timeQueue():
    timeQueue = []
    for filename in os.listdir(folderName):
        if filename.startswith("bsm") and filename.endswith(".json"):
            with open(os.path.join(folderName, filename), "r") as f:
                bsmData = json.load(f)
                timestamp = datetime.strptime(bsmData["timestamp"], "%Y-%m-%dT%H:%M:%SZ")
                timeQueue.append((timestamp, filename))
    # Sort the queue based on timestamp
    timeQueue.sort(key=lambda x: x[0])
    return timeQueue


def process_bsm_files():
    global transaction_count

    # Create the timeQueue sorted by timestamp
    timeQueue = create_timeQueue()

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

        # Forge a block and recalculate trust metrics after 100 transactions
        if transaction_count >= transaction_limit:
            mine_response = requests.get(f"{blockchain_url}/mine")
            print(mine_response.json())

            # Recalculate trust metrics and update reputation scores
            calculateDirectTrust()
            indirectTrustMatrix = calculateIndirectTrust()
            comprehensiveEvaluation = computeComprehensiveEvaluation(directTrustMatrix, indirectTrustMatrix)
            intermediaryOpinionVector = computeIntermediaryOpinion(comprehensiveEvaluation)
            update_reputation_scores(intermediaryOpinionVector, reputation_scores, g)

            print("Updated Reputation Scores:")
            print(reputation_scores)
            print('-' * 100)

            # Update validators based on the latest reputation scores
            updateValidators()

            # Reset transaction count
            transaction_count = 0


# Start the process
process_bsm_files()
