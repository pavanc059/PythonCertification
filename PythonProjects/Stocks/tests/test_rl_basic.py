"""
Basic tests for RL module (without requiring PyTorch/GPU)

Tests module structure and availability.
"""

import pytest


def _check_environment_available():
    """Check if RL environment is available."""
    try:
        from stockiq.models.rl import RL_ENVIRONMENT_AVAILABLE
        return RL_ENVIRONMENT_AVAILABLE
    except ImportError:
        return False


def _check_agents_available():
    """Check if RL agents are available."""
    try:
        from stockiq.models.rl import RL_AGENTS_AVAILABLE
        return RL_AGENTS_AVAILABLE
    except ImportError:
        return False


class TestRLModuleStructure:
    """Test RL module structure and imports."""

    def test_rl_module_importable(self):
        """Test RL module can be imported."""
        import stockiq.models.rl as rl_module
        
        assert rl_module is not None
        assert hasattr(rl_module, "RL_ENVIRONMENT_AVAILABLE")
        assert hasattr(rl_module, "RL_AGENTS_AVAILABLE")

    def test_environment_availability_flag(self):
        """Test environment availability flag exists."""
        from stockiq.models.rl import RL_ENVIRONMENT_AVAILABLE
        
        assert isinstance(RL_ENVIRONMENT_AVAILABLE, bool)

    def test_agents_availability_flag(self):
        """Test agents availability flag exists."""
        from stockiq.models.rl import RL_AGENTS_AVAILABLE
        
        assert isinstance(RL_AGENTS_AVAILABLE, bool)

    @pytest.mark.skipif(
        not _check_environment_available(),
        reason="RL environment dependencies not available"
    )
    def test_trading_environment_class_exists(self):
        """Test TradingEnvironment class can be imported when available."""
        from stockiq.models.rl import TradingEnvironment
        
        assert TradingEnvironment is not None
        assert hasattr(TradingEnvironment, "reset")
        assert hasattr(TradingEnvironment, "step")

    @pytest.mark.skipif(
        not _check_environment_available(),
        reason="RL environment dependencies not available"
    )
    def test_portfolio_state_class_exists(self):
        """Test PortfolioState dataclass can be imported when available."""
        from stockiq.models.rl import PortfolioState
        
        assert PortfolioState is not None

    @pytest.mark.skipif(
        not _check_environment_available(),
        reason="RL environment dependencies not available"
    )
    def test_reward_calculator_exists(self):
        """Test RewardCalculator class can be imported when available."""
        from stockiq.models.rl import RewardCalculator
        
        assert RewardCalculator is not None
        assert hasattr(RewardCalculator, "calculate")

    @pytest.mark.skipif(
        not _check_agents_available(),
        reason="RL agents dependencies not available (PyTorch/Stable-Baselines3)"
    )
    def test_rl_optimizer_class_exists(self):
        """Test RLPortfolioOptimizer class can be imported when available."""
        from stockiq.models.rl import RLPortfolioOptimizer
        
        assert RLPortfolioOptimizer is not None
        assert hasattr(RLPortfolioOptimizer, "train")
        assert hasattr(RLPortfolioOptimizer, "optimize_portfolio")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
