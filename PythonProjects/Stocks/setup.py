"""
Setup script for StockIQ package.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="stockiq",
    version="2.0.0",
    author="StockIQ Team",
    description="Institutional-Grade Stock Analyzer",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "python-dateutil>=2.8.2",
        "pytz>=2023.3",
        "python-dotenv>=1.0.0",
        "yfinance>=0.2.18",
        "pandas>=1.5.0",
        "numpy>=1.24.0",
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=4.9.0",
        "psycopg2-binary>=2.9.0",
        "SQLAlchemy>=2.0.0",
        "alembic>=1.12.0",
        "redis>=5.0.0",
        "celery>=5.3.0",
        "scikit-learn>=1.3.0",
        "xgboost>=2.0.0",
        "shap>=0.42.0",
        "vaderSentiment>=3.3.2",
        "transformers>=4.30.0",
        "torch>=2.0.0",
        "spacy>=3.6.0",
        "streamlit>=1.45.0",
        "plotly>=5.15.0",
        "tenacity>=8.2.0",
        "structlog>=23.1.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-asyncio>=0.21.0",
            "hypothesis>=6.82.0",
            "black>=23.7.0",
            "flake8>=6.1.0",
            "mypy>=1.5.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "stockiq=stockiq.cli:main",
        ],
    },
)
