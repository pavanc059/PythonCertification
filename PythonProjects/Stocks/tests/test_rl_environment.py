"""
Tests for RL Trading Environment

Tests the OpenAI Gym trading environment for portfolio optimization.
"""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from stockiq.models.rl import TradingEnvironment, PortfolioState


@pytest.fixture
def sample_price_data():
    """Generate sample price data for testing."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    tickers = ["AAPL", "MSFT", "GOOGL"]

    # Generate random walk price data
    data = {}
    for ticker in tickers:
        initial_price = 100.0
        returns = np.random.normal(0.001, 0.02, size=100)
        prices = initial_price * np.exp(np.cumsum(returns))
        data[ticker] = prices

    df = pd.DataFrame(data, index=dates)
    return df


@pytest.fixture
def trading_env(sample_price_data):
    """Create trading environment fixture."""
    return TradingEnvironment(
        tickers=["AAPL", "MSFT", "GOOGL"],
        price_data=sample_price_data,
        initial_balance=100000.0,
        transaction_cost=0.001,
        lookback_window=20,
        max_steps=50,
    )


class TestTradingEnvironment:
    """Test suite for TradingEnvironment."""

    def test_environment_initialization(self, trading_env):
        """Test environment initializes correctly."""
        assert trading_env.n_assets == 3
        assert trading_env.initial_balance == 100000.0
        assert trading_env.transaction_cost == 0.001
        assert trading_env.lookback_window == 20
        assert trading_env.max_steps == 50

    def test_action_space_shape(self, trading_env):
        """Test action space has correct dimensions."""
        # n_assets + 1 for cash
        assert trading_env.action_space.shape == (4,)
        assert trading_env.action_space.low.min() == 0.0
        assert trading_env.action_space.high.max() == 1.0

    def test_observation_space_shape(self, trading_env):
        """Test observation space has correct dimensions."""
        n_features = (
            4  # Portfolio weights (3 assets + cash)
            + 1  # Portfolio value (normalized)
            + 3 * 20  # Historical returns (3 assets * 20 lookback)
        )
        assert trading_env.observation_space.shape == (n_features,)

    def test_reset(self, trading_env):
        """Test environment reset."""
        obs, info = trading_env.reset()

        assert isinstance(obs, np.ndarray)
        assert isinstance(info, dict)
        assert trading_env.current_step == 0
        assert trading_env.portfolio_value == 100000.0
        assert trading_env.cash == 100000.0
        assert all(pos == 0 for pos in trading_env.positions.values())

    def test_step_basic(self, trading_env):
        """Test basic step execution."""
        obs, _ = trading_env.reset()

        # Take action: allocate 25% to each asset, 25% cash
        action = np.array([0.25, 0.25, 0.25, 0.25])

        obs, reward, terminated, truncated, info = trading_env.step(action)

        assert isinstance(obs, np.ndarray)
        assert isinstance(reward, (float, np.floating))
        assert isinstance(terminated, bool)
        assert isinstance(truncated, bool)
        assert isinstance(info, dict)
        assert trading_env.current_step == 1

    def test_portfolio_value_updates(self, trading_env):
        """Test portfolio value updates with market movements."""
        trading_env.reset()

        initial_value = trading_env.portfolio_value

        # Take action
        action = np.array([0.3, 0.3, 0.3, 0.1])  # Mostly invested
        trading_env.step(action)

        # Portfolio value should change
        # (Could be higher or lower depending on market movement)
        assert trading_env.portfolio_value != initial_value

    def test_transaction_costs_applied(self, trading_env):
        """Test transaction costs are correctly applied."""
        trading_env.reset()

        # Take action that requires trades
        action = np.array([0.5, 0.5, 0.0, 0.0])
        _, _, _, _, info = trading_env.step(action)

        # Transaction costs should be recorded
        assert "transaction_costs" in info
        assert info["transaction_costs"] >= 0

    def test_action_normalization(self, trading_env):
        """Test action weights are normalized to sum to 1."""
        trading_env.reset()

        # Provide unnormalized action
        action = np.array([1.0, 2.0, 3.0, 4.0])
        trading_env.step(action)

        # Portfolio weights should sum to 1 (within floating point tolerance)
        assert np.isclose(trading_env.portfolio_weights.sum(), 1.0, atol=1e-6)

    def test_episode_termination(self, trading_env):
        """Test episode terminates correctly."""
        obs, _ = trading_env.reset()
        terminated = False
        truncated = False
        steps = 0

        while not (terminated or truncated):
            action = trading_env.action_space.sample()
            obs, reward, terminated, truncated, info = trading_env.step(action)
            steps += 1

            # Prevent infinite loop
            if steps > 1000:
                break

        # Should terminate within max_steps or end of data
        assert terminated or truncated
        assert steps <= trading_env.max_steps

    def test_portfolio_metrics(self, trading_env):
        """Test portfolio metrics calculation."""
        trading_env.reset()

        # Run a few steps
        for _ in range(10):
            action = trading_env.action_space.sample()
            trading_env.step(action)

        metrics = trading_env.get_portfolio_metrics()

        assert "total_return" in metrics
        assert "mean_return" in metrics
        assert "std_return" in metrics
        assert "sharpe_ratio" in metrics
        assert "max_drawdown" in metrics
        assert "final_value" in metrics
        assert "num_trades" in metrics

    def test_positions_tracking(self, trading_env):
        """Test positions are correctly tracked."""
        trading_env.reset()

        # Buy some stocks
        action = np.array([0.3, 0.3, 0.0, 0.4])  # Buy AAPL and MSFT
        trading_env.step(action)

        # Check positions are updated
        assert trading_env.positions["AAPL"] > 0
        assert trading_env.positions["MSFT"] > 0
        assert trading_env.positions["GOOGL"] == 0

    def test_cash_constraint(self, trading_env):
        """Test trades respect cash constraints."""
        trading_env.reset()

        # Try to invest more than 100%
        action = np.array([0.6, 0.6, 0.0, 0.0])  # 120% invested (invalid)
        trading_env.step(action)

        # After normalization and cash constraints, should be valid
        assert trading_env.cash >= 0
        total_value = (
            trading_env.cash
            + sum(
                trading_env.positions[ticker]
                * trading_env.price_data.iloc[trading_env.current_date_idx][ticker]
                for ticker in trading_env.tickers
            )
        )
        assert np.isclose(total_value, trading_env.portfolio_value, rtol=1e-4)

    def test_short_selling_prevented(self, trading_env):
        """Test short selling is prevented (no negative positions)."""
        trading_env.reset()

        # Run multiple random actions
        for _ in range(20):
            action = trading_env.action_space.sample()
            trading_env.step(action)

        # All positions should be non-negative
        for ticker in trading_env.tickers:
            assert trading_env.positions[ticker] >= 0


# Property-based tests
class TestTradingEnvironmentProperties:
    """Property-based tests for TradingEnvironment."""

    @given(
        initial_balance=st.floats(min_value=1000, max_value=1000000),
        transaction_cost=st.floats(min_value=0.0, max_value=0.01),
    )
    @settings(max_examples=20, deadline=2000)
    def test_portfolio_value_non_negative(
        self, sample_price_data, initial_balance, transaction_cost
    ):
        """Portfolio value should never be negative."""
        env = TradingEnvironment(
            tickers=["AAPL", "MSFT", "GOOGL"],
            price_data=sample_price_data,
            initial_balance=initial_balance,
            transaction_cost=transaction_cost,
            max_steps=10,
        )

        env.reset()
        for _ in range(10):
            action = env.action_space.sample()
            _, _, terminated, truncated, _ = env.step(action)
            assert env.portfolio_value >= 0
            if terminated or truncated:
                break

    @given(
        action=st.lists(
            st.floats(min_value=0.0, max_value=1.0), min_size=4, max_size=4
        )
    )
    @settings(max_examples=50, deadline=2000)
    def test_weights_sum_to_one(self, trading_env, action):
        """Portfolio weights should always sum to 1."""
        trading_env.reset()
        action_array = np.array(action)
        trading_env.step(action_array)

        assert np.isclose(trading_env.portfolio_weights.sum(), 1.0, atol=1e-5)

    @given(n_steps=st.integers(min_value=1, max_value=20))
    @settings(max_examples=20, deadline=2000)
    def test_deterministic_reset(self, sample_price_data, n_steps):
        """Reset should produce deterministic initial state."""
        env = TradingEnvironment(
            tickers=["AAPL", "MSFT", "GOOGL"],
            price_data=sample_price_data,
            initial_balance=100000.0,
            max_steps=n_steps,
        )

        obs1, info1 = env.reset(seed=42)
        obs2, info2 = env.reset(seed=42)

        assert np.allclose(obs1, obs2)
        assert info1["portfolio_value"] == info2["portfolio_value"]


class TestPortfolioState:
    """Test PortfolioState dataclass."""

    def test_portfolio_state_creation(self):
        """Test PortfolioState can be created."""
        state = PortfolioState(
            portfolio_weights=np.array([0.3, 0.3, 0.3, 0.1]),
            portfolio_value=100000.0,
            cash=10000.0,
            positions={"AAPL": 100, "MSFT": 100, "GOOGL": 50},
            returns=np.array([0.01, 0.02, -0.01]),
            prices=np.array([150.0, 250.0, 2800.0]),
            features=np.array([0.5, 0.6, 0.7]),
            timestamp=pd.Timestamp("2024-01-01"),
        )

        assert state.portfolio_value == 100000.0
        assert state.cash == 10000.0
        assert len(state.positions) == 3
        assert len(state.portfolio_weights) == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
