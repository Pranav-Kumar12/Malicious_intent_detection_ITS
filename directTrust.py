import json
import os
import math
import numpy as np

folderName = "BSM_Files"

speedAvg = 50  # average speed
speedThresholds = [(0.1, 0.9), (0.3, 0.6), (1.0, 0.1)]  # threshold ratio, trust score
latitudeRange = (37.77, 37.78)  # latitude range
longitudeRange = (-122.42, -122.41)  # longitude range
headingAvg = 180  # average heading

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
# We will be needing both because there can be multiple direct trust valuation for vehicle i from vehicle j as it can receive multiple bsm
# So will average out them.

for filename in os.listdir(folderName):
    if filename.startswith("bsm") and filename.endswith(".json"):
        parts = filename.replace("bsm", "").replace(".json", "").split("_")
        i, j = int(parts[0]), int(parts[1])
        
        with open(os.path.join(folderName, filename), "r") as f:
            bsmData = json.load(f)
        
        speed = bsmData["speed"]
        latitude = bsmData["position"]["latitude"]
        longitude = bsmData["position"]["longitude"]
        heading = bsmData["heading"]
        
        speedTrust = calculateParameterTrust(speed, speedAvg, speedThresholds)
        latitudeTrust = 0.9 if latitudeRange[0] <= latitude <= latitudeRange[1] else 0.5
        longitudeTrust = 0.9 if longitudeRange[0] <= longitude <= longitudeRange[1] else 0.5
        headingTrust = calculateParameterTrust(heading, headingAvg, [(0.1, 0.9), (0.5, 0.6), (1.0, 0.1)])
        
        bsmTrust = geometricMean([speedTrust, latitudeTrust, longitudeTrust, headingTrust])
        
        directTrustMatrix[i-1, j-1] += bsmTrust 
        messageCounts[i-1, j-1] += 1

for i in range(10):
    for j in range(10):
        if messageCounts[i, j] > 0:
            directTrustMatrix[i, j] /= messageCounts[i, j]

print("Direct Trust Matrix:")
print(directTrustMatrix)
