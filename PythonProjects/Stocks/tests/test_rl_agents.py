"""
Tests for RL Agents

Tests the RLPortfolioOptimizer and related components.
"""

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from stockiq.models.rl import RLPortfolioOptimizer, TradingEnvironment
from stockiq.models.rl.rewards import (
    AdaptiveRewardCalculator,
    RewardCalculator,
    RewardMetrics,
)


@pytest.fixture
def sample_price_data():
    """Generate sample price data for testing."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    tickers = ["AAPL", "MSFT", "GOOGL"]

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


class TestRewardCalculator:
    """Test suite for RewardCalculator."""

    def test_return_reward(self):
        """Test simple return-based reward."""
        calculator = RewardCalculator(strategy="return")

        reward = calculator.calculate_return_reward(
            portfolio_return=0.02, transaction_costs=0.001
        )

        # Should be approximately: 1.0 * 0.02 - 0.1 * 0.001 = 0.0199
        assert reward > 0
        assert reward < 0.02

    def test_sharpe_reward(self):
        """Test Sharpe ratio-based reward."""
        calculator = RewardCalculator(strategy="sharpe")

        returns = [0.01, 0.02, -0.01, 0.015, 0.008]
        reward = calculator.calculate_sharpe_reward(returns, transaction_costs=0.001)

        assert isinstance(reward, float)

    def test_sortino_reward(self):
        """Test Sortino ratio-based reward."""
        calculator = RewardCalculator(strategy="sortino")

        returns = [0.01, 0.02, -0.01, 0.015, 0.008]
        reward = calculator.calculate_sortino_reward(returns, transaction_costs=0.001)

        assert isinstance(reward, float)

    def test_calmar_reward(self):
        """Test Calmar ratio-based reward."""
        calculator = RewardCalculator(strategy="calmar")

        returns = [0.01, 0.02, -0.01, 0.015, 0.008]
        reward = calculator.calculate_calmar_reward(returns, transaction_costs=0.001)

        assert isinstance(reward, float)

    def test_multi_objective_reward(self):
        """Test multi-objective reward."""
        calculator = RewardCalculator(strategy="multi_objective")

        returns = [0.01, 0.02, -0.01, 0.015, 0.008]
        reward = calculator.calculate_multi_objective_reward(
            portfolio_return=0.01, returns_history=returns, transaction_costs=0.001
        )

        assert isinstance(reward, float)

    def test_calculate_with_strategy(self):
        """Test calculate method uses correct strategy."""
        returns = [0.01, 0.02, -0.01, 0.015, 0.008]

        for strategy in ["return", "sharpe", "sortino", "calmar", "multi_objective"]:
            calculator = RewardCalculator(strategy=strategy)
            reward = calculator.calculate(
                portfolio_return=0.01,
                returns_history=returns,
                transaction_costs=0.001,
            )
            assert isinstance(reward, float)

    def test_get_metrics(self):
        """Test metrics calculation."""
        calculator = RewardCalculator()

        returns = [0.01, 0.02, -0.01, 0.015, 0.008]
        metrics = calculator.get_metrics(returns, transaction_costs=0.001)

        assert isinstance(metrics, RewardMetrics)
        assert hasattr(metrics, "portfolio_return")
        assert hasattr(metrics, "sharpe_ratio")
        assert hasattr(metrics, "max_drawdown")
        assert hasattr(metrics, "volatility")
        assert hasattr(metrics, "transaction_costs")

    def test_invalid_strategy_raises_error(self):
        """Test invalid strategy raises ValueError."""
        calculator = RewardCalculator(strategy="invalid_strategy")

        with pytest.raises(ValueError):
            calculator.calculate(0.01, [0.01, 0.02], 0.001)


class TestAdaptiveRewardCalculator:
    """Test suite for AdaptiveRewardCalculator."""

    def test_adapt_weights_high_volatility(self):
        """Test weights adapt during high volatility."""
        calculator = AdaptiveRewardCalculator(
            base_return_weight=1.0,
            base_risk_weight=0.5,
            volatility_threshold=0.02,
        )

        # High volatility returns
        high_vol_returns = [0.05, -0.04, 0.06, -0.05, 0.04, -0.03, 0.07, -0.06, 0.05, -0.04]

        calculator.adapt_weights(high_vol_returns)

        # Risk weight should increase
        assert calculator.risk_weight > calculator.base_risk_weight
        # Return weight should decrease
        assert calculator.return_weight < calculator.base_return_weight

    def test_adapt_weights_low_volatility(self):
        """Test weights remain stable during low volatility."""
        calculator = AdaptiveRewardCalculator(
            base_return_weight=1.0,
            base_risk_weight=0.5,
            volatility_threshold=0.02,
        )

        # Low volatility returns
        low_vol_returns = [0.001, 0.002, 0.001, 0.002, 0.001, 0.002, 0.001, 0.002, 0.001, 0.002]

        calculator.adapt_weights(low_vol_returns)

        # Weights should reset to base values
        assert calculator.risk_weight == calculator.base_risk_weight
        assert calculator.return_weight == calculator.base_return_weight

    def test_adaptive_calculate(self):
        """Test adaptive reward calculation."""
        calculator = AdaptiveRewardCalculator()

        returns = [0.01, 0.02, -0.01, 0.015, 0.008]
        reward = calculator.calculate(
            portfolio_return=0.01,
            returns_history=returns,
            transaction_costs=0.001,
        )

        assert isinstance(reward, float)


class TestRLPortfolioOptimizer:
    """Test suite for RLPortfolioOptimizer."""

    @pytest.mark.parametrize("algorithm", ["ppo", "a2c", "sac"])
    def test_optimizer_initialization(self, trading_env, algorithm):
        """Test optimizer initializes with different algorithms."""
        optimizer = RLPortfolioOptimizer(
            algorithm=algorithm,
            env=trading_env,
            verbose=0,
        )

        assert optimizer.algorithm == algorithm
        assert optimizer.model is not None
        assert optimizer.vec_env is not None

    def test_set_environment(self, trading_env):
        """Test setting environment after initialization."""
        optimizer = RLPortfolioOptimizer(algorithm="ppo", verbose=0)

        assert optimizer.env is None
        assert optimizer.model is None

        optimizer.set_environment(trading_env)

        assert optimizer.env is not None
        assert optimizer.model is not None

    def test_train_basic(self, trading_env):
        """Test basic training."""
        optimizer = RLPortfolioOptimizer(
            algorithm="ppo",
            env=trading_env,
            verbose=0,
        )

        # Train for a few timesteps
        optimizer.train(total_timesteps=1000)

        assert len(optimizer.training_history) > 0
        assert optimizer.model is not None

    def test_predict_action(self, trading_env):
        """Test action prediction."""
        optimizer = RLPortfolioOptimizer(
            algorithm="ppo",
            env=trading_env,
            verbose=0,
        )

        optimizer.train(total_timesteps=1000)

        obs, _ = trading_env.reset()
        action = optimizer.predict_action(obs, deterministic=True)

        assert isinstance(action, np.ndarray)
        assert action.shape == (4,)  # 3 assets + cash
        assert np.all(action >= 0)

    def test_optimize_portfolio(self, trading_env):
        """Test portfolio optimization."""
        optimizer = RLPortfolioOptimizer(
            algorithm="ppo",
            env=trading_env,
            verbose=0,
        )

        optimizer.train(total_timesteps=1000)

        obs, _ = trading_env.reset()
        weights = optimizer.optimize_portfolio(obs, deterministic=True)

        assert isinstance(weights, dict)
        assert "AAPL" in weights
        assert "MSFT" in weights
        assert "GOOGL" in weights
        assert "cash" in weights

        # Weights should sum to approximately 1
        total_weight = sum(weights.values())
        assert np.isclose(total_weight, 1.0, atol=1e-2)

    def test_evaluate(self, trading_env, sample_price_data):
        """Test agent evaluation."""
        optimizer = RLPortfolioOptimizer(
            algorithm="ppo",
            env=trading_env,
            verbose=0,
        )

        optimizer.train(total_timesteps=1000)

        # Create separate eval environment
        eval_env = TradingEnvironment(
            tickers=["AAPL", "MSFT", "GOOGL"],
            price_data=sample_price_data,
            initial_balance=100000.0,
            max_steps=30,
        )

        metrics = optimizer.evaluate(eval_env, n_episodes=3)

        assert "mean_return" in metrics
        assert "std_return" in metrics
        assert "mean_length" in metrics
        assert "mean_final_value" in metrics
        assert "mean_sharpe_ratio" in metrics
        assert "mean_max_drawdown" in metrics
        assert metrics["n_episodes"] == 3

    def test_save_and_load(self, trading_env):
        """Test saving and loading model."""
        optimizer = RLPortfolioOptimizer(
            algorithm="ppo",
            env=trading_env,
            verbose=0,
        )

        optimizer.train(total_timesteps=1000)

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "model.zip"

            # Save model
            optimizer.save(save_path)
            assert save_path.exists()

            # Create new optimizer and load
            optimizer2 = RLPortfolioOptimizer(
                algorithm="ppo",
                env=trading_env,
                verbose=0,
            )
            optimizer2.load(save_path)

            # Both should produce same predictions
            obs, _ = trading_env.reset()
            action1 = optimizer.predict_action(obs, deterministic=True)
            action2 = optimizer2.predict_action(obs, deterministic=True)

            assert np.allclose(action1, action2, atol=1e-4)

    def test_training_with_tensorboard(self, trading_env):
        """Test training with TensorBoard logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            optimizer = RLPortfolioOptimizer(
                algorithm="ppo",
                env=trading_env,
                verbose=0,
                tensorboard_log=tmpdir,
            )

            optimizer.train(total_timesteps=1000)

            # Check TensorBoard log directory was created
            log_dirs = list(Path(tmpdir).glob("PPO_*"))
            assert len(log_dirs) > 0

    def test_training_with_eval_callback(self, trading_env, sample_price_data):
        """Test training with evaluation callback."""
        eval_env = TradingEnvironment(
            tickers=["AAPL", "MSFT", "GOOGL"],
            price_data=sample_price_data,
            initial_balance=100000.0,
            max_steps=30,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            optimizer = RLPortfolioOptimizer(
                algorithm="ppo",
                env=trading_env,
                verbose=0,
            )

            optimizer.train(
                total_timesteps=2000,
                eval_env=eval_env,
                eval_freq=500,
                n_eval_episodes=2,
                save_path=tmpdir,
            )

            # Check that evaluation files were created
            log_files = list(Path(tmpdir).glob("*.csv"))
            assert len(log_files) > 0

    def test_invalid_algorithm_raises_error(self, trading_env):
        """Test invalid algorithm raises ValueError."""
        with pytest.raises(ValueError):
            RLPortfolioOptimizer(
                algorithm="invalid_algo",
                env=trading_env,
                verbose=0,
            )

    def test_repr(self, trading_env):
        """Test string representation."""
        optimizer = RLPortfolioOptimizer(
            algorithm="ppo",
            env=trading_env,
            verbose=0,
        )

        repr_str = repr(optimizer)
        assert "RLPortfolioOptimizer" in repr_str
        assert "ppo" in repr_str
        assert "trained" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
