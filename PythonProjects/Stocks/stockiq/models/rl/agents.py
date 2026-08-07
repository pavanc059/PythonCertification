"""
Reinforcement Learning Agents for Portfolio Optimization

Implements PPO, A2C, and SAC agents using Stable-Baselines3.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd
from stable_baselines3 import A2C, PPO, SAC
from stable_baselines3.common.callbacks import BaseCallback, EvalCallback
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

from .environment import TradingEnvironment
from .rewards import RewardCalculator


class TensorboardCallback(BaseCallback):
    """
    Custom callback for logging additional metrics to TensorBoard.
    """

    def __init__(self, verbose: int = 0):
        super().__init__(verbose)
        self.episode_returns = []
        self.episode_lengths = []

    def _on_step(self) -> bool:
        """Called at each step."""
        # Log portfolio value if available
        if "portfolio_value" in self.locals.get("infos", [{}])[0]:
            portfolio_value = self.locals["infos"][0]["portfolio_value"]
            self.logger.record("portfolio/value", portfolio_value)

        return True

    def _on_rollout_end(self) -> None:
        """Called at the end of a rollout."""
        # Log episode statistics
        if len(self.episode_returns) > 0:
            self.logger.record("rollout/ep_rew_mean", np.mean(self.episode_returns))
            self.logger.record("rollout/ep_len_mean", np.mean(self.episode_lengths))
            self.episode_returns = []
            self.episode_lengths = []


class RLPortfolioOptimizer:
    """
    Reinforcement Learning Portfolio Optimizer.

    Supports PPO, A2C, and SAC algorithms for portfolio weight optimization.
    Requirement 13.5: Implement reinforcement learning agents for portfolio optimization.
    """

    def __init__(
        self,
        algorithm: str = "ppo",
        env: Optional[TradingEnvironment] = None,
        learning_rate: float = 3e-4,
        gamma: float = 0.99,
        verbose: int = 1,
        tensorboard_log: Optional[str] = None,
        device: str = "auto",
    ):
        """
        Initialize RL portfolio optimizer.

        Args:
            algorithm: RL algorithm ('ppo', 'a2c', 'sac')
            env: Trading environment (optional, can be set later)
            learning_rate: Learning rate for optimizer
            gamma: Discount factor
            verbose: Verbosity level (0: no output, 1: info, 2: debug)
            tensorboard_log: Path for TensorBoard logs
            device: Device to use ('auto', 'cpu', 'cuda')
        """
        self.algorithm = algorithm.lower()
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.verbose = verbose
        self.tensorboard_log = tensorboard_log
        self.device = device

        self.env = env
        self.model = None
        self.vec_env = None
        self.training_history = []

        if env is not None:
            self._setup_model()

    def _setup_model(self) -> None:
        """Initialize the RL model based on selected algorithm."""
        if self.env is None:
            raise ValueError("Environment must be set before initializing model")

        # Validate environment
        try:
            check_env(self.env)
        except Exception as e:
            print(f"Warning: Environment validation failed: {e}")

        # Wrap environment
        self.vec_env = DummyVecEnv([lambda: self.env])

        # Normalize observations and rewards
        self.vec_env = VecNormalize(
            self.vec_env,
            norm_obs=True,
            norm_reward=True,
            clip_obs=10.0,
            clip_reward=10.0,
        )

        # Initialize model based on algorithm
        if self.algorithm == "ppo":
            self.model = PPO(
                "MlpPolicy",
                self.vec_env,
                learning_rate=self.learning_rate,
                gamma=self.gamma,
                verbose=self.verbose,
                tensorboard_log=self.tensorboard_log,
                device=self.device,
                n_steps=2048,
                batch_size=64,
                n_epochs=10,
                ent_coef=0.01,  # Entropy coefficient for exploration
            )
        elif self.algorithm == "a2c":
            self.model = A2C(
                "MlpPolicy",
                self.vec_env,
                learning_rate=self.learning_rate,
                gamma=self.gamma,
                verbose=self.verbose,
                tensorboard_log=self.tensorboard_log,
                device=self.device,
                n_steps=5,
                ent_coef=0.01,
            )
        elif self.algorithm == "sac":
            self.model = SAC(
                "MlpPolicy",
                self.vec_env,
                learning_rate=self.learning_rate,
                gamma=self.gamma,
                verbose=self.verbose,
                tensorboard_log=self.tensorboard_log,
                device=self.device,
                buffer_size=100000,
                batch_size=256,
                ent_coef="auto",  # Automatic entropy tuning
                tau=0.005,  # Soft update coefficient
            )
        else:
            raise ValueError(
                f"Unknown algorithm: {self.algorithm}. "
                f"Supported: 'ppo', 'a2c', 'sac'"
            )

    def set_environment(self, env: TradingEnvironment) -> None:
        """
        Set or update the trading environment.

        Args:
            env: Trading environment
        """
        self.env = env
        self._setup_model()

    def train(
        self,
        total_timesteps: int = 100000,
        callback: Optional[BaseCallback] = None,
        eval_env: Optional[TradingEnvironment] = None,
        eval_freq: int = 10000,
        n_eval_episodes: int = 5,
        save_path: Optional[str] = None,
    ) -> "RLPortfolioOptimizer":
        """
        Train the RL agent.

        Args:
            total_timesteps: Total number of training timesteps
            callback: Optional custom callback
            eval_env: Optional evaluation environment
            eval_freq: Evaluation frequency (timesteps)
            n_eval_episodes: Number of evaluation episodes
            save_path: Path to save best model

        Returns:
            Self for method chaining
        """
        if self.model is None:
            raise ValueError("Model not initialized. Set environment first.")

        callbacks = []

        # Add TensorBoard callback
        if self.tensorboard_log is not None:
            callbacks.append(TensorboardCallback(verbose=self.verbose))

        # Add evaluation callback if eval_env provided
        if eval_env is not None:
            eval_vec_env = DummyVecEnv([lambda: eval_env])
            eval_vec_env = VecNormalize(
                eval_vec_env,
                norm_obs=True,
                norm_reward=True,
                training=False,  # Don't update stats during eval
            )

            eval_callback = EvalCallback(
                eval_vec_env,
                best_model_save_path=save_path,
                log_path=save_path,
                eval_freq=eval_freq,
                n_eval_episodes=n_eval_episodes,
                deterministic=True,
                render=False,
            )
            callbacks.append(eval_callback)

        # Add custom callback if provided
        if callback is not None:
            callbacks.append(callback)

        # Train model
        print(f"\nTraining {self.algorithm.upper()} agent for {total_timesteps} timesteps...")
        start_time = datetime.now()

        self.model.learn(
            total_timesteps=total_timesteps,
            callback=callbacks if callbacks else None,
            progress_bar=True,
        )

        training_time = (datetime.now() - start_time).total_seconds()
        print(f"Training completed in {training_time:.2f} seconds")

        # Store training info
        self.training_history.append(
            {
                "timestamp": datetime.now(),
                "total_timesteps": total_timesteps,
                "training_time": training_time,
            }
        )

        return self

    def optimize_portfolio(
        self, state: np.ndarray, deterministic: bool = True
    ) -> Dict[str, float]:
        """
        Generate optimal portfolio weights for given state.

        Args:
            state: Current market state observation
            deterministic: Use deterministic policy (no exploration)

        Returns:
            Dictionary mapping tickers to portfolio weights
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        # Normalize observation
        if self.vec_env is not None:
            obs_normalized = self.vec_env.normalize_obs(state)
        else:
            obs_normalized = state

        # Predict action (portfolio weights)
        action, _ = self.model.predict(obs_normalized, deterministic=deterministic)

        # Denormalize if needed and ensure valid weights
        action = np.clip(action, 0, 1)
        action = action / (action.sum() + 1e-8)

        # Map to ticker weights
        if self.env is None:
            raise ValueError("Environment not set")

        weights = {}
        for i, ticker in enumerate(self.env.tickers):
            weights[ticker] = float(action[i])

        # Add cash weight
        weights["cash"] = float(action[-1])

        return weights

    def predict_action(
        self, observation: np.ndarray, deterministic: bool = True
    ) -> np.ndarray:
        """
        Predict action (portfolio weights) for given observation.

        Args:
            observation: Market observation
            deterministic: Use deterministic policy

        Returns:
            Action array (portfolio weights)
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        action, _ = self.model.predict(observation, deterministic=deterministic)
        return action

    def evaluate(
        self,
        env: TradingEnvironment,
        n_episodes: int = 10,
        deterministic: bool = True,
    ) -> Dict[str, float]:
        """
        Evaluate agent performance.

        Args:
            env: Trading environment for evaluation
            n_episodes: Number of evaluation episodes
            deterministic: Use deterministic policy

        Returns:
            Dictionary of evaluation metrics
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        episode_returns = []
        episode_lengths = []
        final_values = []
        sharpe_ratios = []
        max_drawdowns = []

        for episode in range(n_episodes):
            obs, _ = env.reset()
            done = False
            episode_reward = 0
            steps = 0

            while not done:
                action, _ = self.model.predict(obs, deterministic=deterministic)
                obs, reward, terminated, truncated, info = env.step(action)
                done = terminated or truncated
                episode_reward += reward
                steps += 1

            episode_returns.append(episode_reward)
            episode_lengths.append(steps)

            # Get episode metrics
            metrics = env.get_portfolio_metrics()
            final_values.append(metrics.get("final_value", 0))
            sharpe_ratios.append(metrics.get("sharpe_ratio", 0))
            max_drawdowns.append(metrics.get("max_drawdown", 0))

        return {
            "mean_return": np.mean(episode_returns),
            "std_return": np.std(episode_returns),
            "mean_length": np.mean(episode_lengths),
            "mean_final_value": np.mean(final_values),
            "mean_sharpe_ratio": np.mean(sharpe_ratios),
            "mean_max_drawdown": np.mean(max_drawdowns),
            "n_episodes": n_episodes,
        }

    def save(self, path: Union[str, Path]) -> None:
        """
        Save trained model.

        Args:
            path: Path to save model
        """
        if self.model is None:
            raise ValueError("No model to save")

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Save model
        self.model.save(str(path))

        # Save normalization stats
        if self.vec_env is not None:
            vec_normalize_path = path.parent / f"{path.stem}_vec_normalize.pkl"
            self.vec_env.save(str(vec_normalize_path))

        print(f"Model saved to {path}")

    def load(self, path: Union[str, Path]) -> "RLPortfolioOptimizer":
        """
        Load trained model.

        Args:
            path: Path to model file

        Returns:
            Self for method chaining
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")

        # Load model based on algorithm
        if self.algorithm == "ppo":
            self.model = PPO.load(str(path), device=self.device)
        elif self.algorithm == "a2c":
            self.model = A2C.load(str(path), device=self.device)
        elif self.algorithm == "sac":
            self.model = SAC.load(str(path), device=self.device)
        else:
            raise ValueError(f"Unknown algorithm: {self.algorithm}")

        # Load normalization stats if available
        vec_normalize_path = path.parent / f"{path.stem}_vec_normalize.pkl"
        if vec_normalize_path.exists() and self.env is not None:
            self.vec_env = DummyVecEnv([lambda: self.env])
            self.vec_env = VecNormalize.load(str(vec_normalize_path), self.vec_env)
            self.vec_env.training = False  # Don't update stats during inference

        print(f"Model loaded from {path}")
        return self

    def get_training_history(self) -> List[Dict]:
        """
        Get training history.

        Returns:
            List of training session information
        """
        return self.training_history

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"RLPortfolioOptimizer("
            f"algorithm={self.algorithm}, "
            f"trained={self.model is not None})"
        )
