# Institutional-Grade Stock Analyzer

[![CI/CD Pipeline](https://github.com/yourusername/stockiq/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/yourusername/stockiq/actions/workflows/ci-cd.yml)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://hub.docker.com/r/yourusername/stockiq)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A professional-grade stock analysis platform providing AI-powered predictions, real-time market intelligence, and comprehensive analytics.

![StockIQ Dashboard](docs/images/dashboard-preview.png)

## 🚀 Features

### Phase 0: Daily Intelligence System (Current)
- **📊 Daily Top Movers**: Real-time identification of top 20 gainers/losers with 5-minute updates
- **📰 News Analyzer**: NLP-powered processing of news from 10+ sources with sentiment scoring
- **🔮 Daily Predictions**: Next-day price forecasts integrating news sentiment and technical/fundamental signals
- **💰 Penny Stock Dashboard**: Dedicated tracker for penny stocks (<$5) with momentum scoring and risk metrics
- **⚠️ Real-Time Alerts**: Instant notifications when news affects watchlist stocks
- **🤖 AI Summarization**: Automated news summaries and daily market digests

## 🏗️ Architecture

```
stockiq/
├── core/              # Core orchestration and business logic
├── data/              # Data collection and processing
│   ├── collectors/    # Market data, news, fundamentals
│   ├── processors/    # Data validation, normalization
│   └── streams/       # Real-time WebSocket handlers
├── models/            # ML models and predictions
│   ├── ensemble/      # Ensemble models
│   └── features.py    # Feature engineering
├── news/              # News analysis subsystem
│   ├── nlp/           # NLP pipeline (sentiment, NER, summarization)
│   ├── impact/        # News impact analysis
│   ├── alerts/        # Alert generation and delivery
│   └── penny/         # Penny stock momentum analysis
├── ui/                # Streamlit UI components
│   ├── dashboards/    # Dashboard pages
│   └── components/    # Reusable UI components
└── infrastructure/    # Database, cache, tasks, monitoring
```

## 🐳 Quick Start with Docker

### Prerequisites
- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose v2.0+
- Git

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/stockiq.git
cd stockiq
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.docker .env

# Edit .env with your API keys
nano .env  # or use your preferred editor
```

**Required API Keys:**
- `NEWSAPI_KEY` - Get from [NewsAPI.org](https://newsapi.org/)
- `FINNHUB_API_KEY` - Get from [Finnhub.io](https://finnhub.io/)
- `ALPHAVANTAGE_API_KEY` - Get from [Alpha Vantage](https://www.alphavantage.co/)

### 3. Start Services

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 4. Access Application

- **Web Interface**: http://localhost:8501
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## 💻 Local Development Setup

### Prerequisites
- Python 3.8 or higher
- PostgreSQL 14+ with TimescaleDB extension
- Redis 7.0+

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/stockiq.git
cd stockiq
```

2. **Create virtual environment**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Initialize database**
```bash
python scripts/init_db.py
```

6. **Start services**
```bash
# Start Redis (if not running as service)
redis-server

# Start Celery worker
celery -A stockiq.infrastructure.tasks worker --loglevel=info

# Start Celery Beat scheduler
celery -A stockiq.infrastructure.tasks beat --loglevel=info

# Start Streamlit web interface
streamlit run app.py
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=stockiq --cov-report=html

# Run property-based tests
pytest tests/properties/

# Run integration tests
pytest tests/integration/
```

## 📊 Technology Stack

**Backend:**
- Python 3.8+
- PostgreSQL 14+ with TimescaleDB 2.0+
- Redis 7.0+
- Celery 5.0+

**Machine Learning:**
- scikit-learn (traditional ML)
- VADER, FinBERT (sentiment analysis)
- spaCy (NLP)
- SHAP (explainability)

**Data Sources:**
- yfinance (market data)
- NewsAPI, Finnhub, Alpha Vantage (news)
- SEC EDGAR (filings)

**Frontend:**
- Streamlit 1.45.0+
- Plotly 5.15.0+ (charts)

**Infrastructure:**
- Docker & Docker Compose
- GitHub Actions (CI/CD)
- GitHub Container Registry

## 🚢 Deployment

### Docker Compose (Recommended)

See [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) for detailed deployment instructions.

### Cloud Platforms

- **AWS**: ECS/Fargate with RDS and ElastiCache
- **Azure**: Container Instances with Azure Database for PostgreSQL
- **Google Cloud**: Cloud Run with Cloud SQL
- **DigitalOcean**: App Platform with Managed Databases

### GitHub Container Registry

Images are automatically built and pushed to GitHub Container Registry on every push to main:

```bash
docker pull ghcr.io/yourusername/stockiq:latest
```

## 📖 Documentation

- [Setup Guide](SETUP_GUIDE.md) - Detailed setup instructions
- [Docker Deployment](DOCKER_DEPLOYMENT.md) - Docker deployment guide
- [Implementation Status](IMPLEMENTATION_STATUS.md) - Current development status
- [API Documentation](docs/API.md) - API reference (coming soon)
- [Contributing Guide](CONTRIBUTING.md) - How to contribute (coming soon)

## 🗺️ Roadmap

### Phase 0: Daily Intelligence System (Weeks 1-4) - In Progress ✅
- [x] Infrastructure Foundation (Database, Redis, Celery)
- [ ] Data Collection Pipeline
- [ ] News Analysis & Sentiment
- [ ] ML Prediction Engine
- [ ] Penny Stock Analyzer
- [ ] Alert System
- [ ] Daily Dashboard UI

### Phase 1: Infrastructure & Real-Time Data (Weeks 5-8)
- [ ] WebSocket Streaming
- [ ] Database Optimization
- [ ] Cache Optimization
- [ ] API Rate Limiting
- [ ] Monitoring & Logging

### Phase 2: Advanced ML & Analytics (Weeks 9-12)
- [ ] Deep Learning Models (LSTM, Transformers)
- [ ] Reinforcement Learning
- [ ] Options Analytics
- [ ] Risk Analytics
- [ ] Portfolio Optimization

### Phase 3: Alternative Data & Backtesting (Weeks 13-16)
- [ ] SEC Filings Integration
- [ ] Earnings Call Transcripts
- [ ] Insider Trading Data
- [ ] Backtesting Engine
- [ ] Paper Trading

### Phase 4: UI/UX & Advanced Features (Weeks 17-20)
- [ ] Advanced Charting
- [ ] Custom Screeners
- [ ] Customizable Dashboards
- [ ] Mobile-Responsive Design

### Phase 5: Testing, Security & Documentation (Weeks 21-24)
- [ ] Comprehensive Testing
- [ ] Security Audit
- [ ] Performance Optimization
- [ ] Complete Documentation

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) before submitting pull requests.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [TimescaleDB](https://www.timescale.com/) for time-series database
- [Streamlit](https://streamlit.io/) for the amazing web framework
- [yfinance](https://github.com/ranaroussi/yfinance) for market data
- [FinBERT](https://github.com/ProsusAI/finBERT) for financial sentiment analysis

## 📧 Contact

- **GitHub**: [@yourusername](https://github.com/yourusername)
- **Email**: your.email@example.com
- **Website**: https://stockiq.example.com

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=yourusername/stockiq&type=Date)](https://star-history.com/#yourusername/stockiq&Date)

---

**Built with ❤️ for traders and investors**
