from core import data_quality
import pandas as pd
import numpy as np
def main():
    df = pd.read_csv('numerical_cat3')
    df['null_column'] = np.NaN
    dq = data_quality.DataQuality(df)
    results = dq.evaluate()

if __name__ == '__main__':
    main()

