import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from pydantic import ValidationError

from app.core.database import Base
import app.models  # noqa: F401
from app.api.v1.auth import LoginRequest


def constraint_names(table_name, constraint_type):
    return {
        constraint.name
        for constraint in Base.metadata.tables[table_name].constraints
        if isinstance(constraint, constraint_type)
    }


from sqlalchemy import ForeignKeyConstraint, UniqueConstraint


def test_tenant_composite_foreign_keys_are_declared():
    expected = {
        "table_sessions": {"fk_table_session_table_restaurant"},
        "session_participants": {"fk_participant_session_restaurant"},
        "menu_items": {"fk_menu_item_category_restaurant"},
        "orders": {
            "fk_order_session_restaurant",
            "fk_order_participant_restaurant",
        },
        "order_items": {
            "fk_order_item_order_session_restaurant",
            "fk_order_item_menu_restaurant",
        },
        "bills": {"fk_bill_session_restaurant"},
        "bill_items": {
            "fk_bill_item_bill_session_restaurant",
            "fk_bill_item_order_item_session_restaurant",
        },
        "payments": {"fk_payment_bill_restaurant"},
        "service_requests": {
            "fk_service_request_session_restaurant",
            "fk_service_request_participant_session_restaurant",
        },
    }

    for table_name, expected_names in expected.items():
        actual_names = constraint_names(table_name, ForeignKeyConstraint)
        assert expected_names <= actual_names, (
            f"{table_name} is missing: {expected_names - actual_names}"
        )


def test_new_tenant_unique_constraints_are_declared():
    expected = {
        "menu_items": {"uq_menu_item_id_restaurant"},
        "orders": {"uq_order_id_session_restaurant"},
        "order_items": {"uq_order_item_id_session_restaurant"},
        "bills": {"uq_bill_id_session_restaurant"},
        "session_participants": {"uq_participant_id_session_restaurant"},
    }

    for table_name, expected_names in expected.items():
        actual_names = constraint_names(table_name, UniqueConstraint)
        assert expected_names <= actual_names, (
            f"{table_name} is missing: {expected_names - actual_names}"
        )


def test_order_and_bill_items_have_tenant_columns():
    expected = {
        "order_items": {"restaurant_id", "session_id"},
        "bill_items": {"restaurant_id", "session_id"},
    }

    for table_name, expected_columns in expected.items():
        actual_columns = set(Base.metadata.tables[table_name].columns.keys())
        assert expected_columns <= actual_columns


def test_active_table_session_has_partial_unique_index():
    indexes = Base.metadata.tables["table_sessions"].indexes

    active_index = next(
        index for index in indexes
        if index.name == "uq_active_session_per_table"
    )

    assert active_index.unique is True
    assert str(
        active_index.dialect_options["postgresql"]["where"]
    ) == "status = 'active'"


def test_bill_session_is_unique():
    constraints = Base.metadata.tables["bills"].constraints

    assert any(
        getattr(constraint, "name", None) == "uq_bill_session"
        for constraint in constraints
    )


def test_login_input_is_normalized():
    login = LoginRequest(
        restaurant_slug="  Demo-Restaurant ",
        email="  OWNER@EXAMPLE.COM ",
        password="TestPassword123!",
    )

    assert login.restaurant_slug == "demo-restaurant"
    assert login.email == "owner@example.com"


@pytest.mark.parametrize(
    "payload",
    [
        {
            "restaurant_slug": "ab",
            "email": "owner@example.com",
            "password": "Password123!",
        },
        {
            "restaurant_slug": "demo",
            "email": "invalid-email",
            "password": "Password123!",
        },
        {
            "restaurant_slug": "demo",
            "email": "owner@example.com",
            "password": "",
        },
        {
            "restaurant_slug": "demo",
            "email": "owner@example.com",
            "password": "x" * 129,
        },
    ],
)
def test_login_rejects_invalid_input(payload):
    with pytest.raises(ValidationError):
        LoginRequest(**payload)