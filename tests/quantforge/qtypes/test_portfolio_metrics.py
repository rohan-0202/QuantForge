import pytest
from datetime import date, timedelta
import numpy as np
import pandas as pd

from quantforge.qtypes.assetclass import AssetClass
from quantforge.qtypes.portfolio import Portfolio
from quantforge.qtypes.tradeable_item import TradeableItem
from quantforge.qtypes.portfolio_metrics import PortfolioMetrics


@pytest.mark.unit
class TestPortfolioMetricsInitialization:
    """Unit tests for PortfolioMetrics class initialization."""

    @pytest.fixture
    def tradeable_items(self):
        """Return a list of tradeable items for testing."""
        return [TradeableItem(id="AAPL", asset_class=AssetClass.EQUITY)]

    @pytest.fixture
    def start_date(self):
        """Return a start date for testing."""
        return date(2023, 1, 1)

    @pytest.fixture
    def initial_portfolio(self, tradeable_items, start_date):
        """Return a basic portfolio for initializing metrics."""
        return Portfolio(
            initial_cash=100000.0,
            allowed_tradeable_items=tradeable_items,
            start_date=start_date,
        )

    def test_valid_initialization(self, initial_portfolio):
        """Test valid initialization of PortfolioMetrics."""
        metrics = PortfolioMetrics(initial_portfolio)
        assert metrics._start_date == initial_portfolio.start_date
        assert metrics._initial_cash == initial_portfolio.cash
        assert len(metrics.value_history) == 1
        assert metrics.value_history[0] == (initial_portfolio.start_date, initial_portfolio.cash)

    def test_initialization_with_non_portfolio(self):
        """Test initialization with an object that is not a Portfolio."""
        with pytest.raises(TypeError, match="initial_portfolio must be an instance of Portfolio"):
            PortfolioMetrics("not a portfolio")

    def test_initialization_with_zero_cash_portfolio(self, tradeable_items, start_date):
        """Test initialization with a portfolio having zero initial cash."""
        zero_cash_portfolio = Portfolio(
            initial_cash=1.0, # Must be > 0 to avoid init error in Portfolio
            allowed_tradeable_items=tradeable_items,
            start_date=start_date,
        )
        # Manually set cash to 0 for testing the metrics check
        zero_cash_portfolio._cash = 0.0
        # Portfolio init prevents <= 0, so we have to bypass for test
        with pytest.raises(ValueError, match="Initial portfolio cash must be positive"):
              # Re-create the portfolio instance for the test
              portfolio_to_test = Portfolio(
                    initial_cash=1.0, allowed_tradeable_items=tradeable_items, start_date=start_date
              )
              portfolio_to_test._cash = 0.0 # Force zero cash
              PortfolioMetrics(portfolio_to_test)


@pytest.mark.unit
class TestPortfolioMetricsUpdate:
    """Unit tests for the update method of PortfolioMetrics."""

    @pytest.fixture
    def initial_portfolio(self):
        """Return a basic portfolio."""
        return Portfolio(
            initial_cash=100000.0,
            allowed_tradeable_items=[TradeableItem(id="AAPL", asset_class=AssetClass.EQUITY)],
            start_date=date(2023, 1, 1),
        )

    @pytest.fixture
    def metrics(self, initial_portfolio):
        """Return a PortfolioMetrics instance."""
        return PortfolioMetrics(initial_portfolio)

    def test_update_chronological(self, metrics):
        """Test adding values chronologically."""
        date1 = date(2023, 1, 2)
        value1 = 101000.0
        date2 = date(2023, 1, 3)
        value2 = 102000.0

        metrics.update(date1, value1)
        assert len(metrics.value_history) == 2
        assert metrics.value_history[1] == (date1, value1)

        metrics.update(date2, value2)
        assert len(metrics.value_history) == 3
        assert metrics.value_history[2] == (date2, value2)

    def test_update_same_date(self, metrics):
        """Test updating the value for the latest date."""
        date1 = date(2023, 1, 2)
        value1 = 101000.0
        value1_updated = 101500.0

        metrics.update(date1, value1)
        assert len(metrics.value_history) == 2
        assert metrics.value_history[1] == (date1, value1)

        metrics.update(date1, value1_updated) # Update with same date
        assert len(metrics.value_history) == 2 # Length should not change
        assert metrics.value_history[1] == (date1, value1_updated) # Value should be updated

    def test_update_out_of_order(self, metrics):
        """Test adding a value with a date earlier than the last recorded date."""
        date1 = date(2023, 1, 3)
        value1 = 101000.0
        date_earlier = date(2023, 1, 2)
        value_earlier = 100500.0

        metrics.update(date1, value1)

        with pytest.raises(ValueError, match="Dates must be added chronologically"):
            metrics.update(date_earlier, value_earlier)


@pytest.mark.unit
class TestPortfolioMetricsCalculations:
    """Unit tests for metric calculation methods."""

    @pytest.fixture
    def metrics_instance(self):
        """Provides a PortfolioMetrics instance with pre-populated data."""
        portfolio = Portfolio(
            initial_cash=100.0,
            allowed_tradeable_items=[TradeableItem(id="TEST", asset_class=AssetClass.EQUITY)],
            start_date=date(2023, 1, 1),
        )
        metrics = PortfolioMetrics(portfolio)
        # Add some data points for calculation
        metrics.update(date(2023, 1, 2), 101.0) # +1%
        metrics.update(date(2023, 1, 3), 103.02) # +2%
        metrics.update(date(2023, 1, 4), 101.9898) # -1%
        metrics.update(date(2023, 1, 5), 104.029596) # +2%
        return metrics

    @pytest.fixture
    def metrics_flat(self):
        """Provides a PortfolioMetrics instance with flat performance."""
        portfolio = Portfolio(
            initial_cash=100.0,
            allowed_tradeable_items=[TradeableItem(id="TEST", asset_class=AssetClass.EQUITY)],
            start_date=date(2023, 1, 1),
        )
        metrics = PortfolioMetrics(portfolio)
        metrics.update(date(2023, 1, 2), 100.0)
        metrics.update(date(2023, 1, 3), 100.0)
        metrics.update(date(2023, 1, 4), 100.0)
        return metrics

    @pytest.fixture
    def metrics_insufficient_data(self):
         """Provides a PortfolioMetrics instance with only the initial value."""
         portfolio = Portfolio(
            initial_cash=100.0,
            allowed_tradeable_items=[TradeableItem(id="TEST", asset_class=AssetClass.EQUITY)],
            start_date=date(2023, 1, 1),
        )
         return PortfolioMetrics(portfolio)


    # --- Test calculate_returns ---
    def test_calculate_returns_sufficient_data(self, metrics_instance):
        returns = metrics_instance.calculate_returns()
        assert isinstance(returns, pd.Series)
        assert len(returns) == 4 # Initial point doesn't produce a return
        expected_returns = pd.Series([0.01, 0.02, -0.01, 0.02], index=pd.to_datetime([
            date(2023, 1, 2), date(2023, 1, 3), date(2023, 1, 4), date(2023, 1, 5)
        ]), name="PortfolioValue")
        pd.testing.assert_series_equal(returns, expected_returns, check_dtype=False, atol=1e-6)

    def test_calculate_returns_insufficient_data(self, metrics_insufficient_data):
        assert metrics_insufficient_data.calculate_returns() is None

    def test_calculate_returns_flat_data(self, metrics_flat):
        returns = metrics_flat.calculate_returns()
        assert isinstance(returns, pd.Series)
        assert len(returns) == 3
        expected_returns = pd.Series([0.0, 0.0, 0.0], index=pd.to_datetime([
             date(2023, 1, 2), date(2023, 1, 3), date(2023, 1, 4)
        ]), name="PortfolioValue")
        pd.testing.assert_series_equal(returns, expected_returns, check_dtype=False, atol=1e-9)


    # --- Test calculate_annualized_return (CAGR) ---
    def test_calculate_annualized_return_sufficient_data(self, metrics_instance):
        cagr = metrics_instance.calculate_annualized_return()
        assert cagr is not None
        # Manual check: (104.029596 / 100.0) ** (1 / (4 / 365.25)) - 1
        # Duration = 4 days
        duration_years = 4 / 365.25
        expected_cagr = (104.029596 / 100.0) ** (1 / duration_years) - 1
        assert cagr == pytest.approx(expected_cagr)

    def test_calculate_annualized_return_insufficient_data(self, metrics_insufficient_data):
        assert metrics_insufficient_data.calculate_annualized_return() is None

    def test_calculate_annualized_return_flat_data(self, metrics_flat):
         assert metrics_flat.calculate_annualized_return() == pytest.approx(0.0)


    # --- Test calculate_annualized_volatility ---
    def test_calculate_annualized_volatility_sufficient_data(self, metrics_instance):
        volatility = metrics_instance.calculate_annualized_volatility(periods_per_year=252)
        assert volatility is not None
        returns = metrics_instance.calculate_returns()
        expected_vol = np.std(returns) * np.sqrt(252)
        assert volatility == pytest.approx(expected_vol)

    def test_calculate_annualized_volatility_insufficient_data(self, metrics_insufficient_data):
        assert metrics_insufficient_data.calculate_annualized_volatility() is None

    def test_calculate_annualized_volatility_flat_data(self, metrics_flat):
         assert metrics_flat.calculate_annualized_volatility() == pytest.approx(0.0)


    # --- Test calculate_sharpe_ratio ---
    def test_calculate_sharpe_ratio_sufficient_data(self, metrics_instance):
        sharpe = metrics_instance.calculate_sharpe_ratio(risk_free_rate=0.0, periods_per_year=252)
        assert sharpe is not None
        cagr = metrics_instance.calculate_annualized_return()
        annual_vol = metrics_instance.calculate_annualized_volatility(periods_per_year=252)
        expected_sharpe = cagr / annual_vol
        assert sharpe == pytest.approx(expected_sharpe)

    def test_calculate_sharpe_ratio_with_risk_free(self, metrics_instance):
        risk_free = 0.02
        sharpe = metrics_instance.calculate_sharpe_ratio(risk_free_rate=risk_free, periods_per_year=252)
        assert sharpe is not None
        cagr = metrics_instance.calculate_annualized_return()
        annual_vol = metrics_instance.calculate_annualized_volatility(periods_per_year=252)
        expected_sharpe = (cagr - risk_free) / annual_vol
        assert sharpe == pytest.approx(expected_sharpe)

    def test_calculate_sharpe_ratio_insufficient_data(self, metrics_insufficient_data):
        assert metrics_insufficient_data.calculate_sharpe_ratio() is None

    def test_calculate_sharpe_ratio_flat_data(self, metrics_flat):
        # Zero return, zero volatility -> Sharpe should be 0.0
         assert metrics_flat.calculate_sharpe_ratio(risk_free_rate=0.0) == pytest.approx(0.0)
         # Non-zero risk-free rate, zero return, zero volatility -> Sharpe should be -inf (or handled)
         # Current implementation returns 0.0 if return == risk_free, otherwise inf
         # Let's test when risk_free is different from return (0)
         assert metrics_flat.calculate_sharpe_ratio(risk_free_rate=0.02) == -np.inf # Expect -inf when vol=0 and return < risk_free

    # --- Test calculate_max_drawdown ---
    def test_calculate_max_drawdown_sufficient_data(self, metrics_instance):
        max_dd = metrics_instance.calculate_max_drawdown()
        assert max_dd is not None
        # History: 100, 101, 103.02, 101.9898, 104.029596
        # Peaks:   100, 101, 103.02, 103.02,   104.029596
        # Drawdowns: 0, 0, 0, (101.9898 - 103.02)/103.02, 0
        # Max DD: (101.9898 - 103.02) / 103.02 = -0.010000...
        expected_max_dd = (101.9898 - 103.02) / 103.02
        assert max_dd == pytest.approx(expected_max_dd)

    def test_calculate_max_drawdown_insufficient_data(self, metrics_insufficient_data):
        assert metrics_insufficient_data.calculate_max_drawdown() is None

    def test_calculate_max_drawdown_flat_data(self, metrics_flat):
         # No decline means drawdown is 0.0
         assert metrics_flat.calculate_max_drawdown() == pytest.approx(0.0)

    def test_calculate_max_drawdown_monotonic_increase(self):
        # Need at least one allowed item for Portfolio init
        dummy_item = TradeableItem(id="DUMMY", asset_class=AssetClass.EQUITY)
        portfolio = Portfolio(initial_cash=100.0, allowed_tradeable_items=[dummy_item], start_date=date(2023, 1, 1))
        metrics = PortfolioMetrics(portfolio)
        metrics.update(date(2023, 1, 2), 101.0)
        metrics.update(date(2023, 1, 3), 102.0)
        metrics.update(date(2023, 1, 4), 103.0)
        assert metrics.calculate_max_drawdown() == pytest.approx(0.0)


    # --- Test calculate_sortino_ratio ---
    def test_calculate_sortino_ratio_sufficient_data(self, metrics_instance):
        sortino = metrics_instance.calculate_sortino_ratio(risk_free_rate=0.0, periods_per_year=252)
        assert sortino is not None
        # Manual calculation is complex, check edge cases and if it runs
        assert isinstance(sortino, float)

    def test_calculate_sortino_ratio_insufficient_data(self, metrics_insufficient_data):
        assert metrics_insufficient_data.calculate_sortino_ratio() is None

    def test_calculate_sortino_ratio_flat_data(self, metrics_flat):
         # Zero return, zero downside deviation -> should be handled (returns 0.0 as return==risk_free)
         assert metrics_flat.calculate_sortino_ratio(risk_free_rate=0.0) == pytest.approx(0.0)
         # Test with non-zero risk_free rate
         # Return (0) < risk_free (0.01), downside dev is 0 -> -inf
         assert metrics_flat.calculate_sortino_ratio(risk_free_rate=0.01, periods_per_year=252) == pytest.approx(-np.sqrt(252))


    # --- Test calculate_calmar_ratio ---
    def test_calculate_calmar_ratio_sufficient_data(self, metrics_instance):
        calmar = metrics_instance.calculate_calmar_ratio()
        assert calmar is not None
        cagr = metrics_instance.calculate_annualized_return()
        max_dd = metrics_instance.calculate_max_drawdown()
        expected_calmar = cagr / abs(max_dd)
        assert calmar == pytest.approx(expected_calmar)

    def test_calculate_calmar_ratio_insufficient_data(self, metrics_insufficient_data):
        assert metrics_insufficient_data.calculate_calmar_ratio() is None

    def test_calculate_calmar_ratio_flat_data(self, metrics_flat):
         # Zero return, zero drawdown -> Should be 0.0 or inf based on implementation
         # Current impl returns 0.0 if CAGR is 0
         assert metrics_flat.calculate_calmar_ratio() == pytest.approx(0.0)

    def test_calculate_calmar_ratio_monotonic_increase(self):
        # Need at least one allowed item for Portfolio init
        dummy_item = TradeableItem(id="DUMMY", asset_class=AssetClass.EQUITY)
        portfolio = Portfolio(initial_cash=100.0, allowed_tradeable_items=[dummy_item], start_date=date(2023, 1, 1))
        metrics = PortfolioMetrics(portfolio)
        metrics.update(date(2023, 1, 2), 101.0)
        metrics.update(date(2023, 1, 3), 102.0)
        metrics.update(date(2023, 1, 4), 103.0)
        # Positive return, zero drawdown -> should be inf
        assert metrics.calculate_calmar_ratio() == np.inf


    # --- Test get_final_metrics ---
    def test_get_final_metrics_sufficient_data(self, metrics_instance):
        final_metrics = metrics_instance.get_final_metrics(risk_free_rate=0.01, periods_per_year=252)
        assert isinstance(final_metrics, dict)
        assert "message" not in final_metrics
        assert final_metrics["start_date"] == date(2023, 1, 1)
        assert final_metrics["end_date"] == date(2023, 1, 5)
        assert final_metrics["initial_value"] == 100.0
        assert final_metrics["final_value"] == pytest.approx(104.029596)
        assert final_metrics["total_return_pct"] == pytest.approx(4.029596)
        assert final_metrics["annualized_return_pct"] is not None
        assert final_metrics["annualized_volatility_pct"] is not None
        assert final_metrics["sharpe_ratio"] is not None
        assert final_metrics["sortino_ratio"] is not None
        assert final_metrics["max_drawdown_pct"] is not None
        assert final_metrics["calmar_ratio"] is not None
        assert final_metrics["num_data_points"] == 5 # Initial + 4 updates

    def test_get_final_metrics_insufficient_data(self, metrics_insufficient_data):
        final_metrics = metrics_insufficient_data.get_final_metrics()
        assert isinstance(final_metrics, dict)
        assert "message" in final_metrics
        assert "Not enough data points" in final_metrics["message"]
        # Check that calculation keys are absent
        assert "total_return_pct" not in final_metrics
        assert "annualized_return_pct" not in final_metrics
        assert "sharpe_ratio" not in final_metrics
        assert "sortino_ratio" not in final_metrics
        assert "max_drawdown_pct" not in final_metrics
        assert "calmar_ratio" not in final_metrics
        assert "num_data_points" not in final_metrics # This key is also absent 