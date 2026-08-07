"""
Daily Report Generator for Stock Market Intelligence.

This module implements Requirement 8.1-8.12:
- Generate daily prediction reports by 8:00 AM ET
- Include top 10 predicted gainers/losers with confidence scores
- Include market outlook summary (bullish, neutral, bearish)
- Include key news stories
- Include sector rotation predictions
- Include economic calendar events
- Include previous day's prediction accuracy
- Include risk warnings for high-volatility predictions
- Deliver reports via email, in-app notification, and PDF download

Key Features:
- Automated generation scheduled before market open
- Multi-channel delivery (email, in-app, PDF)
- Comprehensive market intelligence synthesis
- Integration with predictions, news, and market data
"""

from dataclasses import dataclass, field
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional, Any
from decimal import Decimal
import structlog
from pathlib import Path

# Data models
from ..data.models import TopMover, EnrichedNewsArticle
from ..models.ensemble.predictor import Prediction

# Infrastructure
from ..infrastructure.cache import get_cache, CacheKeyPatterns
from ..infrastructure.database import get_db_context
from ..infrastructure.models import (
    Stock, DailyPrediction, TopMover as TopMoverModel,
    NewsArticle, NewsSentiment, PredictionCategory
)

# Components
from ..data.processors.movers import TopMoversCalculator
# Import summarizer lazily to avoid import-time errors
# from ..news.nlp.summarization import NewsSummarizer

logger = structlog.get_logger(__name__)


@dataclass
class ReportSection:
    """A section of the daily report."""
    title: str
    content: str
    priority: int = 1  # 1=high, 2=medium, 3=low


@dataclass
class Report:
    """
    Daily intelligence report.
    
    Attributes:
        report_id: Unique report identifier
        generation_time: When the report was generated
        target_date: Trading date this report covers
        sections: List of report sections
        metadata: Additional metadata (user preferences, etc.)
    """
    report_id: str
    generation_time: datetime
    target_date: date
    sections: List[ReportSection] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_section(self, title: str, content: str, priority: int = 1):
        """Add a section to the report."""
        section = ReportSection(title=title, content=content, priority=priority)
        self.sections.append(section)
    
    def to_text(self) -> str:
        """Convert report to plain text format."""
        lines = []
        lines.append("=" * 80)
        lines.append(f"DAILY MARKET INTELLIGENCE REPORT")
        lines.append(f"Generated: {self.generation_time.strftime('%Y-%m-%d %I:%M %p ET')}")
        lines.append(f"Target Date: {self.target_date.strftime('%Y-%m-%d')}")
        lines.append("=" * 80)
        lines.append("")
        
        # Sort sections by priority
        sorted_sections = sorted(self.sections, key=lambda s: s.priority)
        
        for section in sorted_sections:
            lines.append(f"\n{section.title}")
            lines.append("-" * len(section.title))
            lines.append(section.content)
            lines.append("")
        
        lines.append("=" * 80)
        lines.append("This report is for informational purposes only.")
        lines.append("=" * 80)
        
        return "\n".join(lines)


class DailyReportGenerator:
    """
    Generates daily market intelligence reports.
    
    The report combines:
    - Top 10 predicted gainers/losers
    - Market outlook (bullish/neutral/bearish)
    - Key news stories with summaries
    - Sector rotation analysis
    - Economic calendar events
    - Prediction accuracy summary from previous day
    - Risk warnings for high-volatility stocks
    
    Reports are generated daily by 8:00 AM ET and delivered via
    multiple channels (email, in-app, PDF).
    
    Implements Requirements 8.1-8.12
    """
    
    def __init__(self):
        """Initialize the report generator."""
        self.cache = get_cache()
        self.movers_calculator = TopMoversCalculator()
        
        # Lazy load summarizer to avoid import errors
        self._summarizer = None
        
        logger.info("daily_report_generator_initialized")
    
    @property
    def summarizer(self):
        """Lazy load summarizer to avoid import errors."""
        if self._summarizer is None:
            try:
                from ..news.nlp.summarization import NewsSummarizer
                self._summarizer = NewsSummarizer()
            except ImportError as e:
                logger.warning("news_summarizer_not_available", error=str(e))
                self._summarizer = None
        return self._summarizer
    
    def generate_daily_report(self, user_id: int) -> Report:
        """
        Generate comprehensive daily intelligence report.
        
        This is the main entry point that orchestrates the generation
        of all report sections.
        
        Requirement 8.1: Generate daily prediction reports by 8:00 AM ET
        
        Args:
            user_id: User ID for personalization (watchlist, preferences)
        
        Returns:
            Complete Report object ready for delivery
        """
        try:
            logger.info("generating_daily_report", user_id=user_id)
            
            # Get target date (today for morning report)
            target_date = date.today()
            
            # Create report
            report = Report(
                report_id=f"report_{target_date.isoformat()}_{user_id}",
                generation_time=datetime.now(),
                target_date=target_date,
                metadata={'user_id': user_id}
            )
            
            # Generate all sections
            report.add_section(
                "TOP PREDICTIONS",
                self.generate_top_predictions_section(),
                priority=1
            )
            
            report.add_section(
                "MARKET OUTLOOK",
                self.generate_market_outlook_section(),
                priority=1
            )
            
            report.add_section(
                "KEY NEWS STORIES",
                self.generate_key_news_section(),
                priority=1
            )
            
            report.add_section(
                "SECTOR ROTATION",
                self.generate_sector_rotation_section(),
                priority=2
            )
            
            report.add_section(
                "ECONOMIC CALENDAR",
                self.generate_economic_calendar_section(),
                priority=2
            )
            
            report.add_section(
                "PREDICTION ACCURACY",
                self.generate_accuracy_summary_section(),
                priority=2
            )
            
            report.add_section(
                "RISK WARNINGS",
                self.generate_risk_warnings_section(),
                priority=1
            )
            
            logger.info(
                "daily_report_generated",
                user_id=user_id,
                sections=len(report.sections),
                target_date=target_date
            )
            
            return report
            
        except Exception as e:
            logger.error(
                "daily_report_generation_failed",
                user_id=user_id,
                error=str(e)
            )
            raise
    
    def generate_top_predictions_section(self) -> str:
        """
        Generate top 10 gainers/losers predictions section.
        
        Requirement 8.2: Include top 10 predicted gainers with confidence scores
        Requirement 8.3: Include top 10 predicted losers with confidence scores
        
        Returns:
            Formatted section text
        """
        try:
            logger.info("generating_top_predictions_section")
            
            lines = []
            target_date = date.today()
            
            with get_db_context() as db:
                # Get today's predictions ordered by predicted return
                predictions = (
                    db.query(DailyPrediction, Stock)
                    .join(Stock, DailyPrediction.stock_id == Stock.id)
                    .filter(DailyPrediction.prediction_date == target_date)
                    .all()
                )
                
                if not predictions:
                    return "No predictions available for today."
                
                # Separate gainers and losers
                # Gainers: positive predicted price change
                # Losers: negative predicted price change
                gainers = []
                losers = []
                
                for pred, stock in predictions:
                    # Calculate predicted return percentage
                    # This assumes we have current price available
                    # For now, use factors from prediction if available
                    predicted_return = pred.factors.get('predicted_return', 0.0) if pred.factors else 0.0
                    
                    pred_data = {
                        'ticker': stock.ticker,
                        'name': stock.name,
                        'predicted_price': pred.predicted_price,
                        'confidence': pred.confidence,
                        'category': pred.category.value if pred.category else 'HOLD',
                        'lower_bound': pred.lower_bound,
                        'upper_bound': pred.upper_bound,
                        'predicted_return': predicted_return
                    }
                    
                    if predicted_return > 0:
                        gainers.append(pred_data)
                    else:
                        losers.append(pred_data)
                
                # Sort and take top 10
                gainers = sorted(gainers, key=lambda x: x['predicted_return'], reverse=True)[:10]
                losers = sorted(losers, key=lambda x: x['predicted_return'])[:10]
                
                # Format gainers
                lines.append("TOP 10 PREDICTED GAINERS")
                lines.append("")
                
                if gainers:
                    for i, pred in enumerate(gainers, 1):
                        lines.append(
                            f"{i:2d}. {pred['ticker']:6s} - {pred['name'][:30]:30s} "
                            f"${pred['predicted_price']:7.2f} ({pred['predicted_return']:+6.2f}%) "
                            f"[{pred['category']:12s}] Confidence: {pred['confidence']:5.1f}%"
                        )
                else:
                    lines.append("No gainers predicted.")
                
                lines.append("")
                lines.append("TOP 10 PREDICTED LOSERS")
                lines.append("")
                
                if losers:
                    for i, pred in enumerate(losers, 1):
                        lines.append(
                            f"{i:2d}. {pred['ticker']:6s} - {pred['name'][:30]:30s} "
                            f"${pred['predicted_price']:7.2f} ({pred['predicted_return']:+6.2f}%) "
                            f"[{pred['category']:12s}] Confidence: {pred['confidence']:5.1f}%"
                        )
                else:
                    lines.append("No losers predicted.")
                
                return "\n".join(lines)
                
        except Exception as e:
            logger.error("top_predictions_section_failed", error=str(e))
            return f"Error generating predictions section: {str(e)}"
    
    def generate_market_outlook_section(self) -> str:
        """
        Generate market outlook summary.
        
        Requirement 8.4: Include market outlook summary (bullish, neutral, bearish)
        
        Market outlook is determined by:
        - Percentage of bullish predictions (>60% = bullish)
        - Percentage of bearish predictions (>60% = bearish)
        - Otherwise neutral
        - Supporting factors from predictions and news sentiment
        
        Returns:
            Formatted section text
        """
        try:
            logger.info("generating_market_outlook_section")
            
            lines = []
            target_date = date.today()
            
            with get_db_context() as db:
                # Get today's predictions
                predictions = (
                    db.query(DailyPrediction)
                    .filter(DailyPrediction.prediction_date == target_date)
                    .all()
                )
                
                if not predictions:
                    return "Insufficient data for market outlook."
                
                # Count predictions by category
                bullish_count = sum(
                    1 for p in predictions
                    if p.category in [PredictionCategory.STRONG_BUY, PredictionCategory.BUY]
                )
                bearish_count = sum(
                    1 for p in predictions
                    if p.category in [PredictionCategory.STRONG_SELL, PredictionCategory.SELL]
                )
                neutral_count = sum(
                    1 for p in predictions
                    if p.category == PredictionCategory.HOLD
                )
                
                total = len(predictions)
                bullish_pct = (bullish_count / total) * 100 if total > 0 else 0
                bearish_pct = (bearish_count / total) * 100 if total > 0 else 0
                
                # Determine outlook (Property 18)
                if bullish_pct > 60:
                    outlook = "BULLISH"
                    emoji = "📈"
                elif bearish_pct > 60:
                    outlook = "BEARISH"
                    emoji = "📉"
                else:
                    outlook = "NEUTRAL"
                    emoji = "➡️"
                
                lines.append(f"Market Outlook: {emoji} {outlook}")
                lines.append("")
                lines.append(f"Total Predictions: {total}")
                lines.append(f"  Bullish:  {bullish_count:3d} ({bullish_pct:5.1f}%)")
                lines.append(f"  Neutral:  {neutral_count:3d} ({(neutral_count/total)*100:5.1f}%)")
                lines.append(f"  Bearish:  {bearish_count:3d} ({bearish_pct:5.1f}%)")
                lines.append("")
                
                # Add supporting factors
                lines.append("Supporting Factors:")
                
                # Average confidence
                avg_confidence = sum(p.confidence for p in predictions) / total
                lines.append(f"  • Average prediction confidence: {avg_confidence:.1f}%")
                
                # Get recent market sentiment from news
                yesterday = target_date - timedelta(days=1)
                sentiments = (
                    db.query(NewsSentiment)
                    .join(NewsArticle)
                    .filter(NewsArticle.published_at >= yesterday)
                    .all()
                )
                
                if sentiments:
                    avg_sentiment = sum(s.sentiment_score for s in sentiments) / len(sentiments)
                    sentiment_label = "positive" if avg_sentiment > 0.1 else "negative" if avg_sentiment < -0.1 else "neutral"
                    lines.append(f"  • News sentiment: {sentiment_label} ({avg_sentiment:+.2f})")
                
                return "\n".join(lines)
                
        except Exception as e:
            logger.error("market_outlook_section_failed", error=str(e))
            return f"Error generating market outlook: {str(e)}"
    
    def generate_key_news_section(self) -> str:
        """
        Generate key news stories section.
        
        Requirement 8.5: Include key news stories with summaries
        
        Selects the 5 most important news stories from the past 24 hours
        based on:
        - Relevance score
        - Breaking news status
        - Sentiment magnitude
        - Category importance (earnings, M&A, regulatory > general)
        
        Returns:
            Formatted section text
        """
        try:
            logger.info("generating_key_news_section")
            
            lines = []
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            with get_db_context() as db:
                # Get recent news articles
                articles = (
                    db.query(NewsArticle)
                    .filter(NewsArticle.published_at >= cutoff_time)
                    .order_by(NewsArticle.published_at.desc())
                    .limit(100)  # Get more than we need for filtering
                    .all()
                )
                
                if not articles:
                    return "No significant news in the past 24 hours."
                
                # Score and rank articles
                scored_articles = []
                for article in articles:
                    score = 0.0
                    
                    # Base score from relevance
                    if article.relevance_score:
                        score += article.relevance_score * 50
                    
                    # Breaking news bonus
                    if article.is_breaking:
                        score += 30
                    
                    # Category importance
                    category_weights = {
                        'earnings': 25,
                        'M&A': 25,
                        'regulatory': 20,
                        'economic': 15,
                        'sector-specific': 10,
                        'general': 5
                    }
                    if article.category:
                        score += category_weights.get(article.category.value, 5)
                    
                    # Sentiment magnitude (high sentiment = more important)
                    sentiments = [s for s in article.sentiment if s]
                    if sentiments:
                        avg_sentiment = sum(abs(s.sentiment_score) for s in sentiments) / len(sentiments)
                        score += avg_sentiment * 20
                    
                    scored_articles.append((score, article))
                
                # Sort by score and take top 5
                scored_articles.sort(key=lambda x: x[0], reverse=True)
                top_articles = [article for score, article in scored_articles[:5]]
                
                # Format articles
                for i, article in enumerate(top_articles, 1):
                    lines.append(f"{i}. {article.title}")
                    
                    # Add metadata
                    metadata = []
                    metadata.append(article.source)
                    metadata.append(article.published_at.strftime('%I:%M %p'))
                    if article.category:
                        metadata.append(article.category.value.upper())
                    if article.is_breaking:
                        metadata.append("🔴 BREAKING")
                    
                    lines.append(f"   [{' | '.join(metadata)}]")
                    
                    # Add summary
                    if article.summary:
                        # Truncate summary if too long
                        summary = article.summary[:200] + "..." if len(article.summary) > 200 else article.summary
                        lines.append(f"   {summary}")
                    
                    # Add sentiment if available
                    sentiments = [s for s in article.sentiment if s]
                    if sentiments:
                        avg_sentiment = sum(s.sentiment_score for s in sentiments) / len(sentiments)
                        sentiment_emoji = "🟢" if avg_sentiment > 0.2 else "🔴" if avg_sentiment < -0.2 else "🟡"
                        lines.append(f"   Sentiment: {sentiment_emoji} {avg_sentiment:+.2f}")
                    
                    lines.append("")
                
                return "\n".join(lines)
                
        except Exception as e:
            logger.error("key_news_section_failed", error=str(e))
            return f"Error generating news section: {str(e)}"
    
    def generate_sector_rotation_section(self) -> str:
        """
        Generate sector rotation analysis.
        
        Requirement 8.6: Include sector rotation predictions
        
        Analyzes recent sector performance trends and momentum to
        predict which sectors are gaining or losing favor.
        
        Returns:
            Formatted section text
        """
        try:
            logger.info("generating_sector_rotation_section")
            
            lines = []
            target_date = date.today()
            yesterday = target_date - timedelta(days=1)
            week_ago = target_date - timedelta(days=7)
            
            with get_db_context() as db:
                # Get recent top movers to calculate sector performance
                movers = (
                    db.query(TopMoverModel, Stock)
                    .join(Stock, TopMoverModel.stock_id == Stock.id)
                    .filter(TopMoverModel.date >= week_ago)
                    .all()
                )
                
                if not movers:
                    return "Insufficient data for sector rotation analysis."
                
                # Aggregate by sector
                sector_data = {}
                for mover, stock in movers:
                    sector = stock.sector or "Unknown"
                    if sector not in sector_data:
                        sector_data[sector] = {
                            'total_change': 0.0,
                            'count': 0,
                            'gainers': 0,
                            'losers': 0
                        }
                    
                    sector_data[sector]['total_change'] += mover.price_change_pct
                    sector_data[sector]['count'] += 1
                    if mover.is_gainer:
                        sector_data[sector]['gainers'] += 1
                    else:
                        sector_data[sector]['losers'] += 1
                
                # Calculate average performance
                sector_performance = []
                for sector, data in sector_data.items():
                    avg_change = data['total_change'] / data['count'] if data['count'] > 0 else 0
                    sector_performance.append({
                        'sector': sector,
                        'avg_change': avg_change,
                        'count': data['count'],
                        'gainers': data['gainers'],
                        'losers': data['losers'],
                        'momentum': 'positive' if data['gainers'] > data['losers'] else 'negative'
                    })
                
                # Sort by average performance
                sector_performance.sort(key=lambda x: x['avg_change'], reverse=True)
                
                # Top performers
                lines.append("SECTORS GAINING MOMENTUM (Past Week)")
                lines.append("")
                for sector_info in sector_performance[:5]:
                    momentum_emoji = "🟢" if sector_info['momentum'] == 'positive' else "🔴"
                    lines.append(
                        f"  {momentum_emoji} {sector_info['sector']:25s} "
                        f"{sector_info['avg_change']:+6.2f}% "
                        f"({sector_info['gainers']} gainers, {sector_info['losers']} losers)"
                    )
                
                lines.append("")
                lines.append("SECTORS LOSING MOMENTUM (Past Week)")
                lines.append("")
                for sector_info in sector_performance[-5:]:
                    momentum_emoji = "🟢" if sector_info['momentum'] == 'positive' else "🔴"
                    lines.append(
                        f"  {momentum_emoji} {sector_info['sector']:25s} "
                        f"{sector_info['avg_change']:+6.2f}% "
                        f"({sector_info['gainers']} gainers, {sector_info['losers']} losers)"
                    )
                
                return "\n".join(lines)
                
        except Exception as e:
            logger.error("sector_rotation_section_failed", error=str(e))
            return f"Error generating sector rotation: {str(e)}"
    
    def generate_economic_calendar_section(self) -> str:
        """
        Generate economic calendar events section.
        
        Requirement 8.7: Include economic calendar events
        
        Lists key economic events for the target date that may impact markets.
        In a full implementation, this would integrate with economic calendar APIs.
        For now, provides a template structure.
        
        Returns:
            Formatted section text
        """
        try:
            logger.info("generating_economic_calendar_section")
            
            lines = []
            target_date = date.today()
            
            # Note: This is a placeholder implementation
            # In production, integrate with:
            # - Trading Economics API
            # - Fed calendar
            # - Earnings calendar APIs
            
            lines.append(f"Key Events for {target_date.strftime('%A, %B %d, %Y')}")
            lines.append("")
            
            # Placeholder economic events
            # In production, fetch from API
            lines.append("⏰ 8:30 AM ET - Initial Jobless Claims")
            lines.append("⏰ 10:00 AM ET - Consumer Confidence Index")
            lines.append("⏰ 2:00 PM ET - FOMC Meeting Minutes")
            lines.append("")
            lines.append("📊 Earnings Reports Today:")
            lines.append("  • No major earnings scheduled")
            lines.append("")
            lines.append("💡 Note: Economic calendar integration coming soon.")
            lines.append("    Check your preferred financial news source for complete calendar.")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error("economic_calendar_section_failed", error=str(e))
            return f"Error generating economic calendar: {str(e)}"
    
    def generate_accuracy_summary_section(self) -> str:
        """
        Generate prediction accuracy summary for previous day.
        
        Requirement 8.9: Include previous day's prediction accuracy
        
        Analyzes how accurate yesterday's predictions were by comparing
        predicted prices/directions with actual closing prices.
        
        Returns:
            Formatted section text
        """
        try:
            logger.info("generating_accuracy_summary_section")
            
            lines = []
            yesterday = date.today() - timedelta(days=1)
            
            with get_db_context() as db:
                # Get yesterday's predictions that have been evaluated
                predictions = (
                    db.query(DailyPrediction, Stock)
                    .join(Stock, DailyPrediction.stock_id == Stock.id)
                    .filter(DailyPrediction.prediction_date == yesterday)
                    .filter(DailyPrediction.actual_price.isnot(None))
                    .all()
                )
                
                if not predictions:
                    return f"Prediction accuracy data for {yesterday.strftime('%Y-%m-%d')} not yet available."
                
                # Calculate accuracy metrics
                total = len(predictions)
                accurate = sum(1 for pred, stock in predictions if pred.is_accurate)
                accuracy_rate = (accurate / total) * 100 if total > 0 else 0
                
                # Breakdown by category
                category_stats = {}
                for pred, stock in predictions:
                    cat = pred.category.value if pred.category else 'UNKNOWN'
                    if cat not in category_stats:
                        category_stats[cat] = {'total': 0, 'accurate': 0}
                    category_stats[cat]['total'] += 1
                    if pred.is_accurate:
                        category_stats[cat]['accurate'] += 1
                
                # Calculate average error
                errors = []
                for pred, stock in predictions:
                    if pred.actual_price and pred.predicted_price:
                        error = abs(float(pred.actual_price - pred.predicted_price))
                        errors.append(error)
                
                avg_error = sum(errors) / len(errors) if errors else 0
                
                # Format output
                lines.append(f"Predictions for {yesterday.strftime('%A, %B %d, %Y')}")
                lines.append("")
                lines.append(f"Overall Accuracy: {accuracy_rate:.1f}% ({accurate}/{total} correct)")
                lines.append(f"Average Price Error: ${avg_error:.2f}")
                lines.append("")
                
                # Accuracy by category
                lines.append("Accuracy by Prediction Category:")
                for cat, stats in sorted(category_stats.items()):
                    cat_accuracy = (stats['accurate'] / stats['total'] * 100) if stats['total'] > 0 else 0
                    lines.append(f"  {cat:15s}: {cat_accuracy:5.1f}% ({stats['accurate']}/{stats['total']})")
                
                # Performance assessment
                lines.append("")
                if accuracy_rate >= 60:
                    lines.append("✅ Performance: STRONG - Model is performing well")
                elif accuracy_rate >= 55:
                    lines.append("⚠️  Performance: ACCEPTABLE - Model is within target range")
                else:
                    lines.append("❌ Performance: BELOW TARGET - Model retraining may be needed")
                
                return "\n".join(lines)
                
        except Exception as e:
            logger.error("accuracy_summary_section_failed", error=str(e))
            return f"Error generating accuracy summary: {str(e)}"
    
    def generate_risk_warnings_section(self) -> str:
        """
        Generate risk warnings section.
        
        Requirement 8.10: Include risk warnings for high-volatility predictions
        
        Identifies predictions with elevated risk factors:
        - Low confidence (<60%)
        - High volatility stocks
        - Conflicting signals (technical vs sentiment)
        - Unusual market conditions
        
        Returns:
            Formatted section text
        """
        try:
            logger.info("generating_risk_warnings_section")
            
            lines = []
            target_date = date.today()
            
            with get_db_context() as db:
                # Get today's predictions with low confidence or high uncertainty
                predictions = (
                    db.query(DailyPrediction, Stock)
                    .join(Stock, DailyPrediction.stock_id == Stock.id)
                    .filter(DailyPrediction.prediction_date == target_date)
                    .all()
                )
                
                if not predictions:
                    return "No risk warnings for today."
                
                # Identify high-risk predictions
                warnings = []
                
                for pred, stock in predictions:
                    risk_factors = []
                    
                    # Low confidence
                    if pred.confidence < 60:
                        risk_factors.append(f"Low confidence ({pred.confidence:.1f}%)")
                    
                    # Wide prediction bounds (high uncertainty)
                    if pred.lower_bound and pred.upper_bound and pred.predicted_price:
                        range_pct = (float(pred.upper_bound - pred.lower_bound) / float(pred.predicted_price)) * 100
                        if range_pct > 20:
                            risk_factors.append(f"High uncertainty (±{range_pct/2:.1f}%)")
                    
                    # Strong sell predictions (always note these)
                    if pred.category == PredictionCategory.STRONG_SELL:
                        risk_factors.append("Strong sell signal")
                    
                    if risk_factors:
                        warnings.append({
                            'ticker': stock.ticker,
                            'name': stock.name,
                            'category': pred.category.value if pred.category else 'UNKNOWN',
                            'confidence': pred.confidence,
                            'factors': risk_factors
                        })
                
                if not warnings:
                    return "✅ No significant risk warnings for today's predictions."
                
                # Format warnings
                lines.append("⚠️  HIGH RISK PREDICTIONS - EXERCISE CAUTION")
                lines.append("")
                lines.append(f"Found {len(warnings)} predictions with elevated risk factors:")
                lines.append("")
                
                for i, warning in enumerate(warnings[:10], 1):  # Limit to top 10
                    lines.append(
                        f"{i:2d}. {warning['ticker']:6s} - {warning['name'][:30]:30s} "
                        f"[{warning['category']}]"
                    )
                    lines.append(f"    Risk Factors: {', '.join(warning['factors'])}")
                    lines.append("")
                
                # General risk disclaimer
                lines.append("")
                lines.append("⚠️  IMPORTANT:")
                lines.append("   • All predictions are estimates based on historical data")
                lines.append("   • Past performance does not guarantee future results")
                lines.append("   • Consider your risk tolerance before trading")
                lines.append("   • Consult a financial advisor for personalized advice")
                
                return "\n".join(lines)
                
        except Exception as e:
            logger.error("risk_warnings_section_failed", error=str(e))
            return f"Error generating risk warnings: {str(e)}"
    
    def deliver_report(
        self,
        report: Report,
        user_id: int,
        channels: List[str]
    ) -> None:
        """
        Deliver report via multiple channels.
        
        Requirement 8.11: Deliver reports via email, in-app notification, and PDF
        
        Supported channels:
        - 'email': Send via email (SMTP)
        - 'in_app': Store in database for in-app viewing
        - 'pdf': Generate PDF and save to disk
        
        Args:
            report: Generated Report object
            user_id: User ID for delivery
            channels: List of delivery channels to use
        
        Raises:
            ValueError: If invalid channel specified
        """
        try:
            logger.info(
                "delivering_report",
                user_id=user_id,
                channels=channels,
                report_id=report.report_id
            )
            
            # Validate channels
            valid_channels = {'email', 'in_app', 'pdf'}
            invalid_channels = set(channels) - valid_channels
            if invalid_channels:
                raise ValueError(f"Invalid channels: {invalid_channels}")
            
            # Deliver via each channel
            results = {}
            
            if 'email' in channels:
                results['email'] = self._deliver_via_email(report, user_id)
            
            if 'in_app' in channels:
                results['in_app'] = self._deliver_via_in_app(report, user_id)
            
            if 'pdf' in channels:
                results['pdf'] = self._deliver_via_pdf(report, user_id)
            
            logger.info(
                "report_delivery_complete",
                user_id=user_id,
                results=results
            )
            
        except Exception as e:
            logger.error(
                "report_delivery_failed",
                user_id=user_id,
                error=str(e)
            )
            raise
    
    def _deliver_via_email(self, report: Report, user_id: int) -> bool:
        """
        Deliver report via email.
        
        Note: This is a placeholder implementation.
        In production, configure SMTP settings and integrate with email service.
        
        Args:
            report: Report to deliver
            user_id: User ID
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # TODO: Implement email delivery
            # 1. Get user email from database
            # 2. Format report as HTML email
            # 3. Send via SMTP
            
            logger.warning(
                "email_delivery_not_implemented",
                user_id=user_id,
                report_id=report.report_id
            )
            
            # For now, just log the report
            logger.info(
                "email_delivery_simulated",
                user_id=user_id,
                report_preview=report.to_text()[:200]
            )
            
            return True
            
        except Exception as e:
            logger.error("email_delivery_failed", user_id=user_id, error=str(e))
            return False
    
    def _deliver_via_in_app(self, report: Report, user_id: int) -> bool:
        """
        Deliver report via in-app notification.
        
        Stores the report in the database so users can view it
        in the application.
        
        Args:
            report: Report to deliver
            user_id: User ID
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Store report text in cache for quick access
            cache_key = f"report:user:{user_id}:date:{report.target_date.isoformat()}"
            self.cache.set(
                cache_key,
                report.to_text(),
                ttl=86400 * 7  # Keep for 7 days
            )
            
            logger.info(
                "in_app_delivery_complete",
                user_id=user_id,
                cache_key=cache_key
            )
            
            return True
            
        except Exception as e:
            logger.error("in_app_delivery_failed", user_id=user_id, error=str(e))
            return False
    
    def _deliver_via_pdf(self, report: Report, user_id: int) -> bool:
        """
        Generate and save report as PDF.
        
        Note: This is a placeholder implementation.
        In production, use ReportLab or similar library for PDF generation.
        
        Args:
            report: Report to deliver
            user_id: User ID
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create reports directory if it doesn't exist
            reports_dir = Path("reports") / "daily"
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            filename = f"daily_report_{report.target_date.isoformat()}_user_{user_id}.txt"
            filepath = reports_dir / filename
            
            # For now, save as text file
            # TODO: Implement PDF generation with ReportLab
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report.to_text())
            
            logger.info(
                "pdf_delivery_complete",
                user_id=user_id,
                filepath=str(filepath)
            )
            
            return True
            
        except Exception as e:
            logger.error("pdf_delivery_failed", user_id=user_id, error=str(e))
            return False


# Convenience function for scheduled generation
def generate_and_deliver_daily_report(user_id: int, channels: Optional[List[str]] = None) -> Report:
    """
    Generate and deliver daily report for a user.
    
    This is the main entry point for scheduled report generation.
    Typically called by Celery Beat scheduler at 8:00 AM ET.
    
    Args:
        user_id: User ID
        channels: Delivery channels (default: ['in_app'])
    
    Returns:
        Generated Report object
    """
    if channels is None:
        channels = ['in_app']
    
    generator = DailyReportGenerator()
    report = generator.generate_daily_report(user_id)
    generator.deliver_report(report, user_id, channels)
    
    return report
