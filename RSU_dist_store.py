import numpy as np

num_vehicles = 10  # sim 10 vehicles
reputation_scores = np.full((num_vehicles, 3), 0.5)

def update_reputation(vehicle_id, new_reputation_score):
    if 0 <= vehicle_id < num_vehicles:
        # Shifting reputation and then reputation current at 0th index
        reputation_scores[vehicle_id] = np.roll(reputation_scores[vehicle_id], 1)
        reputation_scores[vehicle_id, 0] = new_reputation_score
    else:
        print(f"Error: vehicle_id {vehicle_id} is out of range.")


    

if __name__ == "__main__":
    print("RSU initialized..")