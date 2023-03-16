from core import data_quality
import pandas as pd
import numpy as np


def main():

    # This is just a test dataframe from my own project
    df = pd.read_csv('wine.csv')

    # Adding a column with missing values
    df['null_column'] = np.NaN

    # Adding a two columns that duplicate each other
    df['duplicate_column'] = 6
    df['extra_duplicate_column'] = 6


    dq = data_quality.DataQuality(df)
    results = dq.evaluate()


if __name__ == '__main__':
    main()

