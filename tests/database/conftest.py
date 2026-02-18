"""Fixtures for isolated database module tests.

Provides reusable fixtures for all database test modules, including
a fresh in-memory or temp-file SQLite DatabaseManager for each test.
"""
import os
import shutil
import tempfile
from datetime import datetime, date

import pytest

from database import DatabaseManager
from database.connection import DatabaseConnection
from database.base_crud import BaseCRUD
from database.models import (
    Base, Employee, Customer, ServiceType, Product,
    ReferralChannel, Membership, ServiceRecord, ProductSale,
    RawMessage, Correction, DailySummary, PluginData, InventoryLog,
)
from database.entity_repos import (
    StaffRepository, CustomerRepository, ServiceTypeRepository,
    ProductRepository, ChannelRepository,
)
from database.business_repos import (
    ServiceRecordRepository, ProductSaleRepository, MembershipRepository,
)
from database.system_repos import (
    MessageRepository, SummaryRepository, PluginRepository,
)


@pytest.fixture
def temp_db():
    """Yield a fresh DatabaseManager bound to a temp SQLite database."""
    temp_dir = tempfile.mkdtemp(prefix="db-tests-")
    db_path = os.path.join(temp_dir, "test.db")
    manager = DatabaseManager(database_url=f"sqlite:///{db_path}")
    manager.create_tables()

    try:
        yield manager
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def db_conn(temp_db):
    """Yield a DatabaseConnection from the temp_db manager."""
    return temp_db.conn


@pytest.fixture
def base_crud(db_conn):
    """Yield a BaseCRUD instance."""
    return BaseCRUD(db_conn)


@pytest.fixture
def sample_datetime():
    """Stable datetime value for deterministic tests."""
    return datetime(2024, 1, 28, 10, 0, 0)


@pytest.fixture
def sample_date():
    """Stable date value for deterministic tests."""
    return date(2024, 1, 28)


def make_raw_message(db, suffix="default"):
    """Helper: create a raw message and return its ID."""
    return db.save_raw_message({
        "msg_id": f"msg-{suffix}",
        "sender_nickname": "tester",
        "content": f"test content {suffix}",
        "timestamp": datetime(2024, 1, 28, 10, 0, 0),
    })
