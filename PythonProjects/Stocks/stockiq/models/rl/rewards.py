"""
Reward Functions for RL Portfolio Optimization

Provides various reward calculation strategies for the trading environment.
"""

from dataclasses import dataclass
from typing import Dict, List

import numpy as np


@dataclass
class RewardMetrics:
    """Metrics used for reward calculation"""

    portfolio_return: float
    sharpe_ratio: float
    max_drawdown: float
    volatility: float
    transaction_costs: float


class RewardCalculator:
    """
    Calculates rewards for portfolio optimization.

    Supports multiple reward strategies optimizing for different objectives.
    """

    def __init__(
        self,
        strategy: str = "sharpe",
        risk_free_rate: float = 0.02,  # 2% annual risk-free rate
        return_weight: float = 1.0,
        risk_weight: float = 0.5,
        cost_weight: float = 0.1,
    ):
        """
        Initialize reward calculator.

        Args:
            strategy: Reward strategy ('return', 'sharpe', 'sortino', 'calmar')
            risk_free_rate: Annual risk-free rate for Sharpe/Sortino
            return_weight: Weight for return component
            risk_weight: Weight for risk component
            cost_weight: Weight for transaction cost penalty
        """
        self.strategy = strategy
        self.risk_free_rate = risk_free_rate / 252  # Daily risk-free rate
        self.return_weight = return_weight
        self.risk_weight = risk_weight
        self.cost_weight = cost_weight

    def calculate_return_reward(
        self, portfolio_return: float, transaction_costs: float = 0.0
    ) -> float:
        """
        Simple return-based reward.

        Args:
            portfolio_return: Portfolio return for current step
            transaction_costs: Transaction costs as fraction of portfolio value

        Returns:
            Reward value
        """
        reward = (
            self.return_weight * portfolio_return
            - self.cost_weight * transaction_costs
        )
        return reward

    def calculate_sharpe_reward(
        self,
        returns_history: List[float],
        transaction_costs: float = 0.0,
    ) -> float:
        """
        Sharpe ratio-based reward.

        Args:
            returns_history: Historical returns
            transaction_costs: Transaction costs as fraction of portfolio value

        Returns:
            Reward based on Sharpe ratio
        """
        if len(returns_history) < 2:
            return 0.0

        returns = np.array(returns_history)
        excess_returns = returns - self.risk_free_rate

        mean_return = np.mean(excess_returns)
        std_return = np.std(excess_returns)

        if std_return > 0:
            sharpe = mean_return / std_return
        else:
            sharpe = 0.0

        reward = (
            self.return_weight * sharpe - self.cost_weight * transaction_costs
        )
        return reward

    def calculate_sortino_reward(
        self,
        returns_history: List[float],
        transaction_costs: float = 0.0,
    ) -> float:
        """
        Sortino ratio-based reward (penalizes only downside volatility).

        Args:
            returns_history: Historical returns
            transaction_costs: Transaction costs as fraction of portfolio value

        Returns:
            Reward based on Sortino ratio
        """
        if len(returns_history) < 2:
            return 0.0

        returns = np.array(returns_history)
        excess_returns = returns - self.risk_free_rate

        mean_return = np.mean(excess_returns)

        # Downside deviation (only negative returns)
        downside_returns = excess_returns[excess_returns < 0]
        if len(downside_returns) > 0:
            downside_std = np.std(downside_returns)
        else:
            downside_std = 0.0

        if downside_std > 0:
            sortino = mean_return / downside_std
        else:
            sortino = mean_return if mean_return > 0 else 0.0

        reward = (
            self.return_weight * sortino - self.cost_weight * transaction_costs
        )
        return reward

    def calculate_calmar_reward(
        self,
        returns_history: List[float],
        transaction_costs: float = 0.0,
    ) -> float:
        """
        Calmar ratio-based reward (return / max drawdown).

        Args:
            returns_history: Historical returns
            transaction_costs: Transaction costs as fraction of portfolio value

        Returns:
            Reward based on Calmar ratio
        """
        if len(returns_history) < 2:
            return 0.0

        returns = np.array(returns_history)
        cumulative_returns = np.cumprod(1 + returns)

        # Calculate max drawdown
        cummax = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - cummax) / cummax
        max_drawdown = np.abs(np.min(drawdown))

        mean_return = np.mean(returns)

        if max_drawdown > 0:
            calmar = mean_return / max_drawdown
        else:
            calmar = mean_return if mean_return > 0 else 0.0

        reward = (
            self.return_weight * calmar - self.cost_weight * transaction_costs
        )
        return reward

    def calculate_multi_objective_reward(
        self,
        portfolio_return: float,
        returns_history: List[float],
        transaction_costs: float = 0.0,
    ) -> float:
        """
        Multi-objective reward combining return, risk, and costs.

        Args:
            portfolio_return: Current step return
            returns_history: Historical returns
            transaction_costs: Transaction costs

        Returns:
            Combined reward value
        """
        # Return component
        return_component = self.return_weight * portfolio_return

        # Risk component (penalize volatility)
        if len(returns_history) >= 2:
            volatility = np.std(returns_history)
            risk_component = -self.risk_weight * volatility
        else:
            risk_component = 0.0

        # Cost component
        cost_component = -self.cost_weight * transaction_costs

        reward = return_component + risk_component + cost_component
        return reward

    def calculate(
        self,
        portfolio_return: float,
        returns_history: List[float],
        transaction_costs: float = 0.0,
    ) -> float:
        """
        Calculate reward based on configured strategy.

        Args:
            portfolio_return: Current step return
            returns_history: Historical returns
            transaction_costs: Transaction costs

        Returns:
            Reward value
        """
        if self.strategy == "return":
            return self.calculate_return_reward(portfolio_return, transaction_costs)
        elif self.strategy == "sharpe":
            return self.calculate_sharpe_reward(returns_history, transaction_costs)
        elif self.strategy == "sortino":
            return self.calculate_sortino_reward(returns_history, transaction_costs)
        elif self.strategy == "calmar":
            return self.calculate_calmar_reward(returns_history, transaction_costs)
        elif self.strategy == "multi_objective":
            return self.calculate_multi_objective_reward(
                portfolio_return, returns_history, transaction_costs
            )
        else:
            raise ValueError(f"Unknown reward strategy: {self.strategy}")

    def get_metrics(
        self,
        returns_history: List[float],
        transaction_costs: float = 0.0,
    ) -> RewardMetrics:
        """
        Calculate comprehensive reward metrics.

        Args:
            returns_history: Historical returns
            transaction_costs: Transaction costs

        Returns:
            RewardMetrics object with all metrics
        """
        if len(returns_history) < 2:
            return RewardMetrics(
                portfolio_return=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                volatility=0.0,
                transaction_costs=transaction_costs,
            )

        returns = np.array(returns_history)

        # Portfolio return
        portfolio_return = returns[-1]

        # Sharpe ratio
        excess_returns = returns - self.risk_free_rate
        mean_return = np.mean(excess_returns)
        std_return = np.std(excess_returns)
        sharpe_ratio = mean_return / std_return if std_return > 0 else 0.0

        # Max drawdown
        cumulative_returns = np.cumprod(1 + returns)
        cummax = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - cummax) / cummax
        max_drawdown = np.min(drawdown)

        # Volatility
        volatility = std_return

        return RewardMetrics(
            portfolio_return=portfolio_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            volatility=volatility,
            transaction_costs=transaction_costs,
        )


class AdaptiveRewardCalculator(RewardCalculator):
    """
    Adaptive reward calculator that adjusts weights based on market conditions.

    Increases risk aversion during high volatility periods.
    """

    def __init__(
        self,
        strategy: str = "multi_objective",
        risk_free_rate: float = 0.02,
        base_return_weight: float = 1.0,
        base_risk_weight: float = 0.5,
        base_cost_weight: float = 0.1,
        volatility_threshold: float = 0.02,  # 2% daily volatility threshold
    ):
        """
        Initialize adaptive reward calculator.

        Args:
            strategy: Base reward strategy
            risk_free_rate: Annual risk-free rate
            base_return_weight: Base weight for returns
            base_risk_weight: Base weight for risk
            base_cost_weight: Base weight for costs
            volatility_threshold: Volatility threshold for adaptation
        """
        super().__init__(
            strategy=strategy,
            risk_free_rate=risk_free_rate,
            return_weight=base_return_weight,
            risk_weight=base_risk_weight,
            cost_weight=base_cost_weight,
        )

        self.base_return_weight = base_return_weight
        self.base_risk_weight = base_risk_weight
        self.base_cost_weight = base_cost_weight
        self.volatility_threshold = volatility_threshold

    def adapt_weights(self, returns_history: List[float]) -> None:
        """
        Adapt reward weights based on market volatility.

        Args:
            returns_history: Historical returns
        """
        if len(returns_history) < 10:
            return

        # Calculate recent volatility (last 10 periods)
        recent_returns = np.array(returns_history[-10:])
        recent_volatility = np.std(recent_returns)

        # Increase risk aversion when volatility is high
        if recent_volatility > self.volatility_threshold:
            volatility_multiplier = recent_volatility / self.volatility_threshold
            self.risk_weight = self.base_risk_weight * volatility_multiplier
            # Reduce return weight to balance
            self.return_weight = self.base_return_weight / np.sqrt(volatility_multiplier)
        else:
            # Reset to base weights
            self.return_weight = self.base_return_weight
            self.risk_weight = self.base_risk_weight

    def calculate(
        self,
        portfolio_return: float,
        returns_history: List[float],
        transaction_costs: float = 0.0,
    ) -> float:
        """
        Calculate reward with adaptive weights.

        Args:
            portfolio_return: Current step return
            returns_history: Historical returns
            transaction_costs: Transaction costs

        Returns:
            Reward value with adapted weights
        """
        # Adapt weights based on recent volatility
        self.adapt_weights(returns_history)

        # Calculate reward using parent method with adapted weights
        return super().calculate(portfolio_return, returns_history, transaction_costs)
