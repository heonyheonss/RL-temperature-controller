import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

from scipy.optimize import curve_fit

DIR = "example/"

for filename in os.listdir(DIR):
    if filename.endswith(".csv"):
        df = pd.read_csv(DIR + filename)

def temp_diff(temp_f:float, temp_i:float) -> float:
    return temp_f - temp_i

def lagging_calc(temp_input:float, temp_react:float) -> float:
    return temp_react - temp_input

def time_constant_calc(temp_i:float, temp_react:float) -> float:
    return 0.632*temp_react - temp_i