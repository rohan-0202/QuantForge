import pandas as pd
from quantforge.strategies.abstract_strategy import StrategyInputData
from quantforge.strategies.data_requirement import DataRequirement
from quantforge.db.df_columns import TIMESTAMP, LAST_UPDATED
from datetime import date


def create_masked_data(
    input_data: StrategyInputData, cutoff_date: date
) -> StrategyInputData:
    """
    Create a masked version of input_data that only includes data up to cutoff_date.
    Handles ticker data (timestamp index) and options data (last_updated column) differently.
    """
    # Convert cutoff_date to pandas Timestamp with UTC timezone for proper comparison
    pd_cutoff_date = pd.Timestamp(cutoff_date, tz="UTC")

    masked_data = {}

    for tradeable_item, item_data in input_data.items():
        masked_item_data = {}

        for data_requirement, df in item_data.items():
            # Case 1: TICKER data - use timestamp
            if data_requirement == DataRequirement.TICKER:
                if (
                    isinstance(df.index, pd.DatetimeIndex)
                    and df.index.name == TIMESTAMP
                ):
                    masked_df = df.loc[df.index <= pd_cutoff_date]
                else:
                    # For TICKER data that doesn't have the expected structure
                    raise ValueError(
                        f"TICKER data for {tradeable_item} does not have timestamp index"
                    )

            # Case 2: OPTIONS data - use last_updated column
            elif data_requirement == DataRequirement.OPTIONS:
                if LAST_UPDATED in df.columns:
                    masked_df = df[df[LAST_UPDATED] <= pd_cutoff_date]
                else:
                    raise ValueError(
                        f"OPTIONS data for {tradeable_item} does not have last_updated column"
                    )

            # Case 3: Not implemented for other data requirements
            else:
                raise NotImplementedError(
                    f"Masking not implemented for data requirement: {data_requirement}"
                )

            masked_item_data[data_requirement] = masked_df

        masked_data[tradeable_item] = masked_item_data

    return masked_data
