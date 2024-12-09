import numpy as np
import random

def adjustPrecisionErrors(matrix):
    adjusted_matrix = np.zeros_like(matrix)
    
    for i in range(matrix.shape[0]):  
        for j in range(matrix.shape[1]): 
            if(i!=j):
                adjustment = random.uniform(-0.2, +0.4)
                adjusted_matrix[i, j] = matrix[i, j] + adjustment
        
    return adjusted_matrix
