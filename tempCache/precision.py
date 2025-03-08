import numpy as np
import random

def adjustPrecisionErrors(matrix, val):
    adjusted_matrix = np.zeros_like(matrix)
    print(matrix)
    for i in range(matrix.shape[0]):  
        for j in range(matrix.shape[1]): 
            if(i!=j):
                if(val>0.5):
                    adjustment = random.uniform(-0.1, +0.5)
                    adjusted_matrix[i, j] = matrix[i, j] + adjustment
                else:
                    adjustment = random.uniform(-0.1, +0.3)
                    adjusted_matrix[i, j] = matrix[i, j] + adjustment
                    
        
    return adjusted_matrix
