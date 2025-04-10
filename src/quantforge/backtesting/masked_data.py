import pandas as pd
from quantforge.strategies.abstract_strategy import StrategyInputData


def create_masked_data(input_data: StrategyInputData, cutoff_date) -> StrategyInputData:
    """
    Create a masked version of input_data that only includes data up to cutoff_date.
    Handles ticker data (timestamp index) and options data (last_updated column) differently.
    """
    masked_data = {}

    for tradeable_item, item_data in input_data.items():
        masked_item_data = {}

        for data_requirement, df in item_data.items():
            # Case 1: Regular ticker data with timestamp as index
            if isinstance(df.index, pd.DatetimeIndex) and df.index.name == "timestamp":
                masked_df = df.loc[df.index <= cutoff_date]

            # Case 2: Options data where last_updated is the relevant column (not the index)
            elif "last_updated" in df.columns:
                masked_df = df[df["last_updated"] <= cutoff_date]

            # Case 3: Any other DataFrame with DatetimeIndex
            elif isinstance(df.index, pd.DatetimeIndex):
                masked_df = df.loc[df.index <= cutoff_date]

            # Case 4: Fallback - look for date-like columns
            else:
                date_cols = [
                    col
                    for col in df.columns
                    if col.lower() in ["date", "timestamp", "datetime"]
                ]
                if date_cols:
                    masked_df = df[df[date_cols[0]] <= cutoff_date]
                else:
                    # If no date column found, return the DataFrame as is
                    masked_df = df

            masked_item_data[data_requirement] = masked_df

        masked_data[tradeable_item] = masked_item_data

    return masked_data
