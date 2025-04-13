import datetime
from typing import List, Tuple, Optional, Dict
import numpy as np
import pandas as pd
from quantforge.qtypes.portfolio import Portfolio


class PortfolioMetrics:
    """
    Calculates and stores performance metrics for a portfolio over time.

    Designed to be updated periodically (e.g., daily) during a backtest.
    """

    def __init__(self, initial_portfolio: Portfolio):
        """
        Initializes the metrics tracker with the portfolio's starting state.

        Args:
            initial_portfolio: The portfolio object at the beginning of the backtest.

        Raises:
            TypeError: If initial_portfolio is not a Portfolio instance.
            ValueError: If initial_portfolio has zero or negative initial cash.
        """
        if not isinstance(initial_portfolio, Portfolio):
            raise TypeError("initial_portfolio must be an instance of Portfolio")
        if initial_portfolio.cash <= 0:
             raise ValueError("Initial portfolio cash must be positive for meaningful metrics.")


        self._start_date: datetime.date = initial_portfolio.start_date
        self._initial_cash: float = initial_portfolio.cash
        # Store history as (date, value) tuples, starting with the initial state
        self._value_history: List[Tuple[datetime.date, float]] = [
            (self._start_date, self._initial_cash)
        ]
        # Cache for calculated returns series to avoid recalculation
        self._returns_series: Optional[pd.Series] = None

    @property
    def value_history(self) -> List[Tuple[datetime.date, float]]:
        """Returns the recorded history of portfolio values."""
        return self._value_history

    def update(self, date: datetime.date, portfolio_value: float):
        """
        Records the portfolio's total value for a given date.

        Ensures dates are added chronologically. If the date already exists,
        it updates the value for that date.

        Args:
            date: The date for which the value is recorded.
            portfolio_value: The total value of the portfolio on that date.
        """
        if not self._value_history or date > self._value_history[-1][0]:
            self._value_history.append((date, portfolio_value))
            self._returns_series = None  # Invalidate cache
        elif date == self._value_history[-1][0]:
            # Update value if it's for the same latest date
            self._value_history[-1] = (date, portfolio_value)
            self._returns_series = None  # Invalidate cache
        else:
            # Handle out-of-order updates: find insertion point or raise error
            # For simplicity, we'll raise an error for now.
            # Alternatively, could insert and sort, but that implies backtest isn't strictly chronological.
            raise ValueError(
                f"Date {date} is earlier than the last recorded date {self._value_history[-1][0]}. Dates must be added chronologically."
            )

    def _get_values_series(self) -> Optional[pd.Series]:
        """
        Converts the value history to a pandas Series, indexed by date.
        Handles duplicate dates by keeping the last entry and ensures sorting.
        """
        if len(self._value_history) < 2:
            return None
        dates, values = zip(*self._value_history)
        # Ensure dates are datetime objects for pandas
        datetime_index = pd.to_datetime(dates)
        series = pd.Series(values, index=datetime_index, name="PortfolioValue")
        # Keep last value for duplicate dates (e.g., if update called multiple times for same day)
        series = series[~series.index.duplicated(keep='last')]
        series = series.sort_index() # Ensure chronological order
        return series


    def calculate_returns(self, frequency: str = 'D') -> Optional[pd.Series]:
        """
        Calculates periodic returns based on the value history.
        Currently primarily supports daily ('D') returns calculation.

        Args:
            frequency: The frequency for returns calculation (default 'D').
                       Other frequencies might require resampling logic not yet implemented.

        Returns:
            A pandas Series of returns, or None if not enough data.
        """
        # Use cached daily returns if available and requested
        if self._returns_series is not None and frequency == 'D':
             return self._returns_series

        series = self._get_values_series()
        if series is None or len(series) < 2:
            return None

        # Calculate daily returns
        returns = series.pct_change().dropna()

        # Cache daily returns if calculated
        if frequency == 'D':
            self._returns_series = returns

        # Placeholder for other frequencies:
        # if frequency != 'D':
        #    resampled_values = series.resample(frequency).last()
        #    returns = resampled_values.pct_change().dropna()
        #    print(f"Warning: Calculation for frequency '{frequency}' might need validation.")


        return returns

    def calculate_annualized_return(self) -> Optional[float]:
        """
        Calculates the Compound Annual Growth Rate (CAGR).

        Returns:
            The CAGR as a decimal, or None if not possible.
        """
        if len(self._value_history) < 2:
            return None

        start_date = self._value_history[0][0]
        end_date = self._value_history[-1][0]
        start_value = self._value_history[0][1]
        end_value = self._value_history[-1][1]

        if start_value <= 0: # Avoid division by zero or log(negative)
            return None

        delta_days = (end_date - start_date).days
        if delta_days <= 0:
            return 0.0 # No time elapsed, or only one data point

        duration_years = delta_days / 365.25
        cagr = (end_value / start_value) ** (1 / duration_years) - 1

        return cagr

    def calculate_annualized_volatility(self, periods_per_year: int = 252) -> Optional[float]:
        """
        Calculates the annualized volatility (standard deviation of returns).

        Args:
            periods_per_year: Number of trading periods in a year (e.g., 252 for daily data).

        Returns:
            The annualized volatility as a decimal, or None if not possible.
        """
        daily_returns = self.calculate_returns(frequency='D')
        if daily_returns is None or daily_returns.empty:
            return None

        volatility = np.std(daily_returns)
        annualized_volatility = volatility * np.sqrt(periods_per_year)
        return annualized_volatility

    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.0, periods_per_year: int = 252) -> Optional[float]:
        """
        Calculates the annualized Sharpe Ratio using daily returns.

        Args:
            risk_free_rate: The annual risk-free rate (as a decimal, e.g., 0.02 for 2%).
            periods_per_year: Number of trading periods in a year (e.g., 252 for daily data).

        Returns:
            The annualized Sharpe Ratio, or None if calculation is not possible.
        """
        daily_returns = self.calculate_returns(frequency='D')
        if daily_returns is None or daily_returns.empty:
            return None

        # Use annualized metrics for clearer calculation
        annual_return = self.calculate_annualized_return()
        annual_volatility = self.calculate_annualized_volatility(periods_per_year)

        if annual_return is None or annual_volatility is None:
            return None

        # Avoid division by zero if volatility is zero
        if np.isclose(annual_volatility, 0):
            # If return equals risk-free rate, Sharpe is 0, otherwise infinite
            if np.isclose(annual_return, risk_free_rate):
                return 0.0
            elif annual_return > risk_free_rate:
                return np.inf
            else: # annual_return < risk_free_rate
                return -np.inf

        sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility
        return sharpe_ratio

    def calculate_sortino_ratio(self, risk_free_rate: float = 0.0, periods_per_year: int = 252) -> Optional[float]:
        """
        Calculates the annualized Sortino Ratio.

        Args:
            risk_free_rate: The annual target rate (usually risk-free rate).
            periods_per_year: Number of trading periods in a year.

        Returns:
            The annualized Sortino Ratio, or None if not possible.
        """
        daily_returns = self.calculate_returns(frequency='D')
        if daily_returns is None or daily_returns.empty:
            return None

        annual_return = self.calculate_annualized_return()
        if annual_return is None:
            return None

        target_return_daily = risk_free_rate / periods_per_year

        # Calculate downside returns (returns below the target)
        downside_returns = daily_returns[daily_returns < target_return_daily] - target_return_daily

        # Calculate Downside Deviation
        if downside_returns.empty:
             downside_deviation = 0.0 # No returns were below target
        else:
            # Calculate variance of downside returns, then take sqrt
            downside_variance = (downside_returns ** 2).sum() / len(daily_returns) # Use total N for sample std dev
            downside_deviation = np.sqrt(downside_variance)

        # Annualize downside deviation
        annualized_downside_deviation = downside_deviation * np.sqrt(periods_per_year)

        # Avoid division by zero
        if np.isclose(annualized_downside_deviation, 0):
             # If return > risk-free, ratio is effectively infinite, otherwise 0
             if np.isclose(annual_return, risk_free_rate):
                 return 0.0
             elif annual_return > risk_free_rate:
                 return np.inf
             else: # annual_return < risk_free_rate
                 return -np.inf

        sortino_ratio = (annual_return - risk_free_rate) / annualized_downside_deviation
        return sortino_ratio

    def calculate_max_drawdown(self) -> Optional[float]:
        """
        Calculates the maximum drawdown experienced by the portfolio.

        Drawdown is calculated as the largest peak-to-trough decline.

        Returns:
            The maximum drawdown as a negative decimal (e.g., -0.2 for 20% decline),
            or 0.0 if no drawdown occurred, or None if not enough data.
        """
        series = self._get_values_series()
        if series is None or len(series) < 2:
            return None

        cumulative_max = series.cummax()
        # Calculate drawdown relative to the peak
        # Ensure cumulative_max is not zero to avoid division errors, although init checks initial cash > 0
        drawdown = (series - cumulative_max) / cumulative_max.replace(0, np.nan) # Avoid division by zero if peak hits 0

        max_drawdown = drawdown.min()

        # If max_drawdown is NaN (e.g., only one data point, or div by zero), return None or 0.0
        if pd.isna(max_drawdown) or not np.isfinite(max_drawdown):
             return 0.0 # No decline measurable

        return max_drawdown # Returns the minimum value, which represents the largest drop

    def calculate_calmar_ratio(self) -> Optional[float]:
        """
        Calculates the Calmar Ratio (Annualized Return / Absolute Max Drawdown).

        Returns:
            The Calmar Ratio, or None if not possible.
        """
        annual_return = self.calculate_annualized_return()
        max_dd = self.calculate_max_drawdown()

        if annual_return is None or max_dd is None:
            return None

        # Avoid division by zero if max drawdown is zero
        if np.isclose(max_dd, 0):
            # If return is positive, ratio is infinite, otherwise 0 or undefined depending on perspective
            return np.inf if annual_return > 0 else 0.0

        calmar_ratio = annual_return / abs(max_dd)
        return calmar_ratio


    def get_final_metrics(self, risk_free_rate: float = 0.0, periods_per_year: int = 252) -> Dict[str, Optional[any]]:
        """
        Calculates and returns a dictionary of final performance metrics.

        Args:
            risk_free_rate: The annual risk-free rate for Sharpe/Sortino calculation.
            periods_per_year: Number of trading periods in a year for annualization.

        Returns:
            A dictionary containing key performance metrics. Values might be None if
            calculation wasn't possible.
        """
        if len(self._value_history) < 2:
            return {
                "start_date": self._start_date,
                "end_date": self._value_history[-1][0] if self._value_history else self._start_date,
                "initial_value": self._initial_cash,
                "final_value": self._value_history[-1][1] if self._value_history else self._initial_cash,
                "message": "Not enough data points to calculate performance metrics."
            }

        final_value = self._value_history[-1][1]
        total_return = (final_value / self._initial_cash) - 1
        cagr = self.calculate_annualized_return()
        annual_vol = self.calculate_annualized_volatility(periods_per_year)
        sharpe = self.calculate_sharpe_ratio(risk_free_rate, periods_per_year)
        sortino = self.calculate_sortino_ratio(risk_free_rate, periods_per_year)
        max_dd = self.calculate_max_drawdown()
        calmar = self.calculate_calmar_ratio()


        return {
            "start_date": self._start_date,
            "end_date": self._value_history[-1][0],
            "initial_value": self._initial_cash,
            "final_value": final_value,
            "total_return_pct": total_return * 100,
            "annualized_return_pct": (cagr * 100) if cagr is not None else None,
            "annualized_volatility_pct": (annual_vol * 100) if annual_vol is not None else None,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "max_drawdown_pct": (max_dd * 100) if max_dd is not None else None,
            "calmar_ratio": calmar,
            "num_data_points": len(self._value_history)
        } 