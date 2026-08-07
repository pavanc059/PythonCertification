"""
Trading Environment for Reinforcement Learning

OpenAI Gym-compatible environment for portfolio optimization.
Supports continuous action spaces for portfolio weight allocation.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import gymnasium as gym
import numpy as np
import pandas as pd
from gymnasium import spaces


@dataclass
class PortfolioState:
    """Represents the current state of the portfolio"""

    portfolio_weights: np.ndarray  # Current allocation weights
    portfolio_value: float  # Total portfolio value
    cash: float  # Available cash
    positions: Dict[str, float]  # Ticker -> number of shares
    returns: np.ndarray  # Historical returns
    prices: np.ndarray  # Current prices
    features: np.ndarray  # Technical/fundamental features
    timestamp: datetime  # Current timestamp


class TradingEnvironment(gym.Env):
    """
    OpenAI Gym environment for portfolio trading.

    Action Space: Continuous, representing target portfolio weights for each asset.
    Observation Space: Portfolio state including prices, returns, features.

    Requirement 13.5: Reinforcement learning agents for portfolio optimization
    """

    metadata = {"render_modes": ["human"], "render_fps": 1}

    def __init__(
        self,
        tickers: List[str],
        price_data: pd.DataFrame,
        feature_data: Optional[pd.DataFrame] = None,
        initial_balance: float = 100000.0,
        transaction_cost: float = 0.001,  # 0.1% transaction cost
        lookback_window: int = 60,  # Days of historical data in observation
        max_steps: int = 252,  # Trading days in a year
    ):
        """
        Initialize trading environment.

        Args:
            tickers: List of stock tickers to trade
            price_data: Historical price data (multi-index: date, ticker)
            feature_data: Optional technical/fundamental features
            initial_balance: Starting cash balance
            transaction_cost: Cost per transaction as fraction of trade value
            lookback_window: Number of historical time steps in observation
            max_steps: Maximum steps per episode
        """
        super().__init__()

        self.tickers = tickers
        self.n_assets = len(tickers)
        self.price_data = price_data
        self.feature_data = feature_data
        self.initial_balance = initial_balance
        self.transaction_cost = transaction_cost
        self.lookback_window = lookback_window
        self.max_steps = max_steps

        # Validate price data
        if price_data.empty:
            raise ValueError("Price data cannot be empty")

        # Calculate returns
        self.returns = price_data.pct_change().fillna(0)

        # Define action space: portfolio weights (sum to 1, including cash)
        # Weights for each asset + cash weight
        self.action_space = spaces.Box(
            low=0.0, high=1.0, shape=(self.n_assets + 1,), dtype=np.float32
        )

        # Define observation space
        # Features: [portfolio_weights, portfolio_value, returns_history, price_features]
        n_features = (
            self.n_assets + 1  # Portfolio weights + cash
            + 1  # Portfolio value (normalized)
            + self.n_assets * self.lookback_window  # Historical returns
        )

        if feature_data is not None:
            n_features += feature_data.shape[1]

        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(n_features,), dtype=np.float32
        )

        # Episode state
        self.current_step = 0
        self.current_date_idx = 0
        self.portfolio_value = initial_balance
        self.cash = initial_balance
        self.positions = {ticker: 0.0 for ticker in tickers}
        self.portfolio_weights = np.zeros(self.n_assets + 1)
        self.portfolio_weights[-1] = 1.0  # Start with 100% cash

        # Performance tracking
        self.portfolio_history = []
        self.trades_history = []

    def reset(
        self, seed: Optional[int] = None, options: Optional[dict] = None
    ) -> Tuple[np.ndarray, dict]:
        """
        Reset environment to initial state.

        Returns:
            observation: Initial observation
            info: Additional information dictionary
        """
        super().reset(seed=seed)

        # Reset episode state
        self.current_step = 0
        # Start after lookback window to have historical data
        self.current_date_idx = self.lookback_window

        self.portfolio_value = self.initial_balance
        self.cash = self.initial_balance
        self.positions = {ticker: 0.0 for ticker in self.tickers}
        self.portfolio_weights = np.zeros(self.n_assets + 1)
        self.portfolio_weights[-1] = 1.0  # 100% cash

        # Clear history
        self.portfolio_history = [self.portfolio_value]
        self.trades_history = []

        observation = self._get_observation()
        info = self._get_info()

        return observation, info

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, dict]:
        """
        Execute one time step within the environment.

        Args:
            action: Target portfolio weights (must sum to 1)

        Returns:
            observation: Next observation
            reward: Reward for this step
            terminated: Whether episode ended naturally
            truncated: Whether episode was truncated
            info: Additional information
        """
        # Normalize action to ensure weights sum to 1
        action = np.clip(action, 0, 1)
        action = action / (action.sum() + 1e-8)

        # Calculate required trades to reach target weights
        trades = self._calculate_trades(action)

        # Execute trades and apply transaction costs
        transaction_costs = self._execute_trades(trades)

        # Move to next time step
        self.current_step += 1
        self.current_date_idx += 1

        # Update portfolio value based on market movements
        self._update_portfolio_value()

        # Calculate reward
        reward = self._calculate_reward()

        # Update portfolio weights after market movement
        self._update_portfolio_weights()

        # Check if episode is done
        terminated = self.current_date_idx >= len(self.price_data) - 1
        truncated = self.current_step >= self.max_steps

        # Get next observation
        observation = self._get_observation()
        info = self._get_info()
        info["transaction_costs"] = transaction_costs

        # Track history
        self.portfolio_history.append(self.portfolio_value)

        return observation, reward, terminated, truncated, info

    def _get_observation(self) -> np.ndarray:
        """Construct observation vector from current state."""
        obs_components = []

        # 1. Current portfolio weights (including cash)
        obs_components.append(self.portfolio_weights)

        # 2. Normalized portfolio value
        normalized_value = self.portfolio_value / self.initial_balance
        obs_components.append(np.array([normalized_value]))

        # 3. Historical returns (lookback window)
        start_idx = max(0, self.current_date_idx - self.lookback_window)
        end_idx = self.current_date_idx

        returns_window = self.returns.iloc[start_idx:end_idx].values.flatten()

        # Pad if necessary
        if len(returns_window) < self.n_assets * self.lookback_window:
            padding = np.zeros(
                self.n_assets * self.lookback_window - len(returns_window)
            )
            returns_window = np.concatenate([padding, returns_window])

        obs_components.append(returns_window)

        # 4. Additional features if provided
        if self.feature_data is not None:
            features = self.feature_data.iloc[self.current_date_idx].values
            obs_components.append(features)

        # Concatenate all components
        observation = np.concatenate(obs_components).astype(np.float32)

        return observation

    def _get_info(self) -> dict:
        """Get additional information about current state."""
        return {
            "portfolio_value": self.portfolio_value,
            "cash": self.cash,
            "positions": self.positions.copy(),
            "portfolio_weights": self.portfolio_weights.copy(),
            "current_step": self.current_step,
            "current_date_idx": self.current_date_idx,
        }

    def _calculate_trades(self, target_weights: np.ndarray) -> Dict[str, float]:
        """
        Calculate required trades to reach target portfolio weights.

        Args:
            target_weights: Target weights for each asset + cash

        Returns:
            Dictionary of ticker -> shares to trade (positive = buy, negative = sell)
        """
        trades = {}
        current_prices = self.price_data.iloc[self.current_date_idx]

        for i, ticker in enumerate(self.tickers):
            target_weight = target_weights[i]
            current_weight = self.portfolio_weights[i]

            # Calculate target and current dollar amounts
            target_value = target_weight * self.portfolio_value
            current_value = current_weight * self.portfolio_value

            # Calculate shares to trade
            price = current_prices[ticker]
            if price > 0:
                target_shares = target_value / price
                current_shares = self.positions[ticker]
                shares_to_trade = target_shares - current_shares
                trades[ticker] = shares_to_trade

        return trades

    def _execute_trades(self, trades: Dict[str, float]) -> float:
        """
        Execute trades and update positions and cash.

        Args:
            trades: Dictionary of ticker -> shares to trade

        Returns:
            Total transaction costs
        """
        total_transaction_cost = 0.0
        current_prices = self.price_data.iloc[self.current_date_idx]

        for ticker, shares in trades.items():
            if abs(shares) < 1e-6:  # Skip negligible trades
                continue

            price = current_prices[ticker]
            trade_value = abs(shares * price)
            transaction_cost = trade_value * self.transaction_cost

            if shares > 0:  # Buy
                cost = trade_value + transaction_cost
                if cost <= self.cash:
                    self.positions[ticker] += shares
                    self.cash -= cost
                    total_transaction_cost += transaction_cost
                    self.trades_history.append(
                        {
                            "step": self.current_step,
                            "ticker": ticker,
                            "shares": shares,
                            "price": price,
                            "cost": transaction_cost,
                        }
                    )
            else:  # Sell
                if self.positions[ticker] >= abs(shares):
                    proceeds = trade_value - transaction_cost
                    self.positions[ticker] += shares  # shares is negative
                    self.cash += proceeds
                    total_transaction_cost += transaction_cost
                    self.trades_history.append(
                        {
                            "step": self.current_step,
                            "ticker": ticker,
                            "shares": shares,
                            "price": price,
                            "cost": transaction_cost,
                        }
                    )

        return total_transaction_cost

    def _update_portfolio_value(self) -> None:
        """Update portfolio value based on current prices."""
        current_prices = self.price_data.iloc[self.current_date_idx]

        # Calculate value of positions
        positions_value = sum(
            self.positions[ticker] * current_prices[ticker] for ticker in self.tickers
        )

        self.portfolio_value = self.cash + positions_value

    def _update_portfolio_weights(self) -> None:
        """Update portfolio weights based on current positions and prices."""
        if self.portfolio_value <= 0:
            self.portfolio_weights = np.zeros(self.n_assets + 1)
            return

        current_prices = self.price_data.iloc[self.current_date_idx]

        for i, ticker in enumerate(self.tickers):
            position_value = self.positions[ticker] * current_prices[ticker]
            self.portfolio_weights[i] = position_value / self.portfolio_value

        # Cash weight
        self.portfolio_weights[-1] = self.cash / self.portfolio_value

    def _calculate_reward(self) -> float:
        """
        Calculate reward for current step.
        Uses portfolio return as base reward.
        """
        if len(self.portfolio_history) < 2:
            return 0.0

        # Portfolio return since last step
        prev_value = self.portfolio_history[-1]
        current_value = self.portfolio_value
        portfolio_return = (current_value - prev_value) / prev_value

        return portfolio_return

    def render(self, mode: str = "human") -> None:
        """Render environment state (for debugging)."""
        if mode == "human":
            print(f"\n=== Step {self.current_step} ===")
            print(f"Portfolio Value: ${self.portfolio_value:,.2f}")
            print(f"Cash: ${self.cash:,.2f}")
            print(f"Positions: {self.positions}")
            print(f"Weights: {self.portfolio_weights}")

    def get_portfolio_metrics(self) -> Dict[str, float]:
        """
        Calculate portfolio performance metrics.

        Returns:
            Dictionary of performance metrics
        """
        if len(self.portfolio_history) < 2:
            return {}

        portfolio_values = np.array(self.portfolio_history)
        returns = np.diff(portfolio_values) / portfolio_values[:-1]

        total_return = (portfolio_values[-1] - portfolio_values[0]) / portfolio_values[0]
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        sharpe_ratio = (
            mean_return / std_return * np.sqrt(252) if std_return > 0 else 0
        )

        # Max drawdown
        cummax = np.maximum.accumulate(portfolio_values)
        drawdown = (portfolio_values - cummax) / cummax
        max_drawdown = np.min(drawdown)

        return {
            "total_return": total_return,
            "mean_return": mean_return,
            "std_return": std_return,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "final_value": portfolio_values[-1],
            "num_trades": len(self.trades_history),
        }
