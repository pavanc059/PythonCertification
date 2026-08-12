"""
Unit tests for paper trading ORM models and TradingService.

Tests use an in-memory SQLite database so no running PostgreSQL is required.
SQLite does not support Numeric(18,6) perfectly but handles the basic
insert/query cycle well enough to validate model correctness.

Requirements: R4.1, R4.3, R7.8
"""

import sys
import os
import uuid
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# Make sure we can import backend modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Patch the database URL before importing Base-dependent models
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from database import Base

# Import models under test
from trading.models import PaperTradingAccountDB, PaperOrderDB, PaperPositionDB
from auth.models import User


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def engine():
    """Create an in-memory SQLite engine for testing."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    # SQLite needs UUID support — store as string
    from sqlalchemy import event as _event

    @_event.listens_for(eng, "connect")
    def set_sqlite_pragma(dbapi_con, _):
        dbapi_con.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def db(engine):
    """Return a fresh session for each test, rolled back on teardown."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def user(db):
    """Create and persist a test user."""
    u = User(
        id=uuid.uuid4(),
        email=f"test_{uuid.uuid4().hex[:6]}@example.com",
        name="Test User",
        hashed_password="hashed",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestPaperTradingAccountDB:
    def test_create_account_defaults(self, db, user):
        """Account is created with $100 K defaults (R4.1)."""
        account = PaperTradingAccountDB(user_id=user.id)
        db.add(account)
        db.commit()
        db.refresh(account)

        assert account.id is not None
        assert account.user_id == user.id
        assert float(account.cash) == pytest.approx(100000.0)
        assert float(account.initial_cash) == pytest.approx(100000.0)
        assert account.created_at is not None

    def test_account_is_unique_per_user(self, db, user):
        """Only one account per user (unique constraint on user_id)."""
        a1 = PaperTradingAccountDB(user_id=user.id)
        db.add(a1)
        db.commit()

        a2 = PaperTradingAccountDB(user_id=user.id)
        db.add(a2)
        with pytest.raises(Exception):  # IntegrityError or similar
            db.commit()
        db.rollback()

    def test_relationships_are_accessible(self, db, user):
        """Account exposes positions and orders relationship lists."""
        account = PaperTradingAccountDB(user_id=user.id)
        db.add(account)
        db.commit()
        db.refresh(account)

        assert account.positions == []
        assert account.orders == []


class TestPaperPositionDB:
    def test_create_position(self, db, user):
        """Position row is created with correct fields."""
        account = PaperTradingAccountDB(user_id=user.id)
        db.add(account)
        db.commit()
        db.refresh(account)

        pos = PaperPositionDB(
            account_id=account.id,
            ticker="AAPL",
            quantity=10,
            avg_entry_price=Decimal("150.00"),
            current_price=Decimal("155.00"),
            entry_time=datetime.utcnow(),
        )
        db.add(pos)
        db.commit()
        db.refresh(pos)

        assert pos.id is not None
        assert pos.ticker == "AAPL"
        assert pos.quantity == 10
        assert float(pos.avg_entry_price) == pytest.approx(150.0)

    def test_position_belongs_to_account(self, db, user):
        """Position.account relationship resolves correctly."""
        account = PaperTradingAccountDB(user_id=user.id)
        db.add(account)
        db.commit()

        pos = PaperPositionDB(
            account_id=account.id,
            ticker="TSLA",
            quantity=5,
            avg_entry_price=Decimal("200.00"),
            current_price=Decimal("210.00"),
            entry_time=datetime.utcnow(),
        )
        db.add(pos)
        db.commit()
        db.refresh(pos)

        assert pos.account.id == account.id


class TestPaperOrderDB:
    def test_create_order(self, db, user):
        """Order row is persisted with all required fields."""
        account = PaperTradingAccountDB(user_id=user.id)
        db.add(account)
        db.commit()

        order = PaperOrderDB(
            account_id=account.id,
            order_id=str(uuid.uuid4()),
            ticker="MSFT",
            side="buy",
            order_type="market",
            quantity=20,
            status="filled",
            filled_price=Decimal("320.50"),
            filled_quantity=20,
            commission=Decimal("0"),
            slippage=Decimal("0.32"),
            created_at=datetime.utcnow(),
            filled_at=datetime.utcnow(),
        )
        db.add(order)
        db.commit()
        db.refresh(order)

        assert order.id is not None
        assert order.ticker == "MSFT"
        assert order.status == "filled"
        assert float(order.filled_price) == pytest.approx(320.5)

    def test_order_id_is_unique(self, db, user):
        """order_id field has a unique constraint."""
        account = PaperTradingAccountDB(user_id=user.id)
        db.add(account)
        db.commit()

        shared_id = str(uuid.uuid4())
        o1 = PaperOrderDB(
            account_id=account.id,
            order_id=shared_id,
            ticker="GOOG",
            side="buy",
            order_type="limit",
            quantity=1,
            status="pending",
            limit_price=Decimal("100.00"),
            filled_quantity=0,
            commission=Decimal("0"),
            slippage=Decimal("0"),
            created_at=datetime.utcnow(),
        )
        db.add(o1)
        db.commit()

        o2 = PaperOrderDB(
            account_id=account.id,
            order_id=shared_id,  # duplicate
            ticker="GOOG",
            side="sell",
            order_type="limit",
            quantity=1,
            status="pending",
            filled_quantity=0,
            commission=Decimal("0"),
            slippage=Decimal("0"),
            created_at=datetime.utcnow(),
        )
        db.add(o2)
        with pytest.raises(Exception):
            db.commit()
        db.rollback()

    def test_nullable_price_fields(self, db, user):
        """limit_price and stop_price can be None for market orders."""
        account = PaperTradingAccountDB(user_id=user.id)
        db.add(account)
        db.commit()

        order = PaperOrderDB(
            account_id=account.id,
            order_id=str(uuid.uuid4()),
            ticker="NVDA",
            side="buy",
            order_type="market",
            quantity=3,
            status="filled",
            limit_price=None,
            stop_price=None,
            filled_price=Decimal("450.00"),
            filled_quantity=3,
            commission=Decimal("0"),
            slippage=Decimal("0"),
            created_at=datetime.utcnow(),
            filled_at=datetime.utcnow(),
        )
        db.add(order)
        db.commit()
        db.refresh(order)

        assert order.limit_price is None
        assert order.stop_price is None


# ---------------------------------------------------------------------------
# TradingService tests (integration-style with SQLite)
# ---------------------------------------------------------------------------


class TestTradingService:
    def test_get_or_create_account(self, db, user):
        """TradingService auto-creates account if none exists (R4.1)."""
        from trading.service import TradingService

        service = TradingService(db=db, user_id=user.id)
        assert service.account_db is not None
        assert float(service.account_db.cash) == pytest.approx(100000.0)

    def test_hydrate_account_cash(self, db, user):
        """Hydrated in-memory account reflects DB cash balance (R4.3)."""
        # Pre-create account with modified cash
        account = PaperTradingAccountDB(
            user_id=user.id,
            cash=Decimal("75000"),
            initial_cash=Decimal("100000"),
        )
        db.add(account)
        db.commit()

        from trading.service import TradingService

        service = TradingService(db=db, user_id=user.id)
        assert float(service.account.cash) == pytest.approx(75000.0)

    def test_get_account_summary_returns_dict(self, db, user):
        """get_account_summary returns a dict with expected keys."""
        from trading.service import TradingService

        service = TradingService(db=db, user_id=user.id)
        summary = service.get_account_summary()

        assert isinstance(summary, dict)
        for key in (
            "account_id",
            "cash",
            "portfolio_value",
            "total_value",
            "buying_power",
            "total_return",
            "total_return_pct",
            "num_positions",
            "num_pending_orders",
            "created_at",
        ):
            assert key in summary, f"Missing key: {key}"

    def test_get_positions_empty(self, db, user):
        """get_positions returns an empty list for a fresh account."""
        from trading.service import TradingService

        service = TradingService(db=db, user_id=user.id)
        assert service.get_positions() == []

    def test_get_orders_empty(self, db, user):
        """get_orders returns an empty list for a fresh account."""
        from trading.service import TradingService

        service = TradingService(db=db, user_id=user.id)
        assert service.get_orders() == []

    def test_reset_account(self, db, user):
        """reset_account restores cash to initial_cash and clears positions/orders."""
        account = PaperTradingAccountDB(
            user_id=user.id,
            cash=Decimal("55000"),
            initial_cash=Decimal("100000"),
        )
        db.add(account)
        db.commit()

        # Add a position so we can verify it gets cleared
        pos = PaperPositionDB(
            account_id=account.id,
            ticker="AAPL",
            quantity=10,
            avg_entry_price=Decimal("150"),
            current_price=Decimal("155"),
            entry_time=datetime.utcnow(),
        )
        db.add(pos)
        db.commit()

        from trading.service import TradingService

        service = TradingService(db=db, user_id=user.id)
        service.reset_account()

        # Cash should be restored
        db.refresh(service.account_db)
        assert float(service.account_db.cash) == pytest.approx(100000.0)

        # Positions cleared
        remaining = (
            db.query(PaperPositionDB)
            .filter_by(account_id=account.id)
            .count()
        )
        assert remaining == 0

    def test_place_order_unknown_type(self, db, user):
        """place_order returns rejected status for an unknown order type."""
        from trading.service import TradingService

        service = TradingService(db=db, user_id=user.id)
        result = service.place_order(
            ticker="AAPL",
            side="buy",
            order_type="unknown_type",
            quantity=10,
        )
        assert result["status"] == "rejected"
