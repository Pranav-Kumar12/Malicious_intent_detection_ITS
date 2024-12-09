import numpy as np

# Initialize the RSU (Roadside Unit) reputation scores for each vehicle with 0.5
num_vehicles = 10
reputation_scores = np.full((num_vehicles, 3), 0.5)

# Function to update the reputation scores for a given vehicle
def update_reputation(vehicle_id, new_reputation_score):
    if 0 <= vehicle_id < num_vehicles:
        reputation_scores[vehicle_id] = np.roll(reputation_scores[vehicle_id], 1)
        reputation_scores[vehicle_id, 0] = new_reputation_score
    else:
        print(f"Error: vehicle_id {vehicle_id} is out of range.")
