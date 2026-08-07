"""
Database connection management with SQLAlchemy.

This module provides secure database access with:
- Parameterized query enforcement
- SQL injection prevention
- Connection pooling
- Transaction management
"""

from typing import Generator, Dict, Any, List, Optional
from contextlib import contextmanager
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import QueuePool
import structlog

from .config import get_settings

logger = structlog.get_logger(__name__)

# Try to import security module
try:
    from .security_middleware import validate_sql_query_params, SQLInjectionException
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False
    SQLInjectionException = Exception

# Base class for all ORM models
Base = declarative_base()

# Global engine and session factory
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the database engine."""
    global _engine
    
    if _engine is None:
        settings = get_settings()
        
        _engine = create_engine(
            settings.database_url,
            poolclass=QueuePool,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,  # Verify connections before using
            echo=settings.debug,  # Log SQL queries in debug mode
        )
        
        # Add event listener for connection
        @event.listens_for(_engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            logger.info("database_connection_established")
        
        logger.info(
            "database_engine_created",
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
        )
    
    return _engine


def get_session_factory():
    """Get or create the session factory."""
    global _SessionLocal
    
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
        )
        logger.info("database_session_factory_created")
    
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Get a database session.
    
    Usage:
        with get_db() as db:
            # Use db session
            pass
    
    Or in FastAPI/dependency injection:
        def endpoint(db: Session = Depends(get_db)):
            pass
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions.
    
    Usage:
        with get_db_context() as db:
            # Use db session
            pass
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("database_transaction_failed", error=str(e))
        raise
    finally:
        db.close()


def init_db():
    """Initialize the database by creating all tables."""
    from .models import Base  # Import here to avoid circular imports
    
    engine = get_engine()
    
    logger.info("initializing_database")
    Base.metadata.create_all(bind=engine)
    logger.info("database_initialized")


def drop_db():
    """Drop all tables from the database. USE WITH CAUTION!"""
    from .models import Base  # Import here to avoid circular imports
    
    engine = get_engine()
    
    logger.warning("dropping_all_database_tables")
    Base.metadata.drop_all(bind=engine)
    logger.warning("database_tables_dropped")


def close_db():
    """Close the database engine and dispose of connections."""
    global _engine, _SessionLocal
    
    if _engine is not None:
        logger.info("closing_database_engine")
        _engine.dispose()
        _engine = None
        _SessionLocal = None
        logger.info("database_engine_closed")


# ============================================================================
# SQL Injection Prevention Utilities
# ============================================================================

def execute_safe_query(
    db: Session,
    query: str,
    params: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Execute a parameterized query with SQL injection prevention.
    
    This function enforces parameterized queries and validates parameters
    for additional security.
    
    Args:
        db: Database session
        query: SQL query with named parameters (:param_name)
        params: Dictionary of parameter values
        
    Returns:
        Query result
        
    Raises:
        SQLInjectionException: If SQL injection detected
        ValueError: If query is not properly parameterized
        
    Example:
        result = execute_safe_query(
            db,
            "SELECT * FROM stocks WHERE ticker = :ticker",
            {"ticker": "AAPL"}
        )
    """
    if params is None:
        params = {}
    
    # Validate that query uses parameterized placeholders
    if not _is_parameterized_query(query):
        raise ValueError(
            "Query must use parameterized placeholders (:param_name). "
            "String concatenation is not allowed for security."
        )
    
    # Validate parameters for SQL injection
    if SECURITY_AVAILABLE:
        params = validate_sql_query_params(params)
    
    # Execute with text() for explicit parameterization
    result = db.execute(text(query), params)
    
    logger.info(
        "safe_query_executed",
        query_preview=query[:100],
        param_count=len(params)
    )
    
    return result


def _is_parameterized_query(query: str) -> bool:
    """
    Check if query uses parameterized placeholders.
    
    Args:
        query: SQL query string
        
    Returns:
        True if query appears to be parameterized
    """
    # Check for named parameters (:param)
    import re
    has_params = bool(re.search(r':\w+', query))
    
    # Check for suspicious string concatenation patterns
    # These are red flags for SQL injection vulnerabilities
    dangerous_patterns = [
        r'\+\s*["\']',  # String concatenation with +
        r'["\']\\s*\+',  # String concatenation
        r'%s',  # Python string formatting
        r'\.format\(',  # .format() method
        r'f["\']',  # f-strings
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, query):
            logger.warning(
                "dangerous_query_pattern",
                pattern=pattern,
                query_preview=query[:100]
            )
            return False
    
    return True


def build_safe_filter(
    column_name: str,
    operator: str,
    value: Any
) -> tuple[str, Dict[str, Any]]:
    """
    Build a safe SQL filter clause with parameterization.
    
    Args:
        column_name: Name of column to filter
        operator: SQL operator (=, !=, >, <, >=, <=, LIKE, IN)
        value: Filter value
        
    Returns:
        Tuple of (where_clause, parameters)
        
    Example:
        clause, params = build_safe_filter("ticker", "=", "AAPL")
        # Returns: ("ticker = :ticker_0", {"ticker_0": "AAPL"})
    """
    # Validate column name (prevent SQL injection via column names)
    if not _is_safe_identifier(column_name):
        raise ValueError(f"Invalid column name: {column_name}")
    
    # Validate operator
    allowed_operators = ['=', '!=', '>', '<', '>=', '<=', 'LIKE', 'IN', 'NOT IN']
    if operator.upper() not in allowed_operators:
        raise ValueError(f"Invalid operator: {operator}")
    
    # Generate parameter name
    param_name = f"{column_name}_filter"
    
    # Build clause based on operator
    if operator.upper() in ['IN', 'NOT IN']:
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{operator} requires a list or tuple")
        # Create parameter for each value
        param_names = [f"{param_name}_{i}" for i in range(len(value))]
        params = {name: val for name, val in zip(param_names, value)}
        param_list = ', '.join([f":{name}" for name in param_names])
        clause = f"{column_name} {operator} ({param_list})"
    else:
        clause = f"{column_name} {operator} :{param_name}"
        params = {param_name: value}
    
    return clause, params


def _is_safe_identifier(identifier: str) -> bool:
    """
    Check if identifier (table/column name) is safe.
    
    Args:
        identifier: Table or column name
        
    Returns:
        True if safe
    """
    # Only allow alphanumeric and underscore
    import re
    return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier))


def build_safe_query(
    table_name: str,
    columns: List[str],
    filters: Optional[List[tuple[str, str, Any]]] = None,
    order_by: Optional[List[tuple[str, str]]] = None,
    limit: Optional[int] = None
) -> tuple[str, Dict[str, Any]]:
    """
    Build a safe SELECT query with parameterization.
    
    Args:
        table_name: Name of table
        columns: List of column names to select
        filters: List of (column, operator, value) tuples
        order_by: List of (column, direction) tuples
        limit: Maximum number of rows
        
    Returns:
        Tuple of (query, parameters)
        
    Example:
        query, params = build_safe_query(
            "stocks",
            ["ticker", "price"],
            filters=[("market_cap", ">", 1000000)],
            order_by=[("ticker", "ASC")],
            limit=10
        )
    """
    # Validate identifiers
    if not _is_safe_identifier(table_name):
        raise ValueError(f"Invalid table name: {table_name}")
    
    for col in columns:
        if not _is_safe_identifier(col):
            raise ValueError(f"Invalid column name: {col}")
    
    # Build SELECT clause
    columns_str = ', '.join(columns)
    query = f"SELECT {columns_str} FROM {table_name}"
    
    # Build WHERE clause
    all_params = {}
    if filters:
        where_clauses = []
        for i, (column, operator, value) in enumerate(filters):
            clause, params = build_safe_filter(column, operator, value)
            # Make parameter names unique
            unique_params = {f"{k}_{i}": v for k, v in params.items()}
            clause = clause.replace(f":{list(params.keys())[0]}", f":{list(unique_params.keys())[0]}")
            where_clauses.append(clause)
            all_params.update(unique_params)
        
        query += " WHERE " + " AND ".join(where_clauses)
    
    # Build ORDER BY clause
    if order_by:
        order_clauses = []
        for column, direction in order_by:
            if not _is_safe_identifier(column):
                raise ValueError(f"Invalid column name: {column}")
            if direction.upper() not in ['ASC', 'DESC']:
                raise ValueError(f"Invalid order direction: {direction}")
            order_clauses.append(f"{column} {direction}")
        
        query += " ORDER BY " + ", ".join(order_clauses)
    
    # Add LIMIT
    if limit is not None:
        if not isinstance(limit, int) or limit < 0:
            raise ValueError("Limit must be a non-negative integer")
        query += f" LIMIT {limit}"
    
    return query, all_params
