"""enforce tenant consistency with composite foreign keys

Revision ID: c4f19a72d8e1
Revises: 1a3a0652b9ca
Create Date: 2026-11-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c4f19a72d8e1"
down_revision: Union[str, Sequence[str], None] = "1a3a0652b9ca"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fail before changing schema if existing rows violate tenant ownership.
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1 FROM table_sessions s
            JOIN dining_tables t ON t.id = s.table_id
            WHERE t.restaurant_id <> s.restaurant_id
        ) OR EXISTS (
            SELECT 1 FROM session_participants p
            JOIN table_sessions s ON s.id = p.session_id
            WHERE s.restaurant_id <> p.restaurant_id
        ) OR EXISTS (
            SELECT 1 FROM menu_items i
            JOIN menu_categories c ON c.id = i.category_id
            WHERE c.restaurant_id <> i.restaurant_id
        ) OR EXISTS (
            SELECT 1 FROM orders o
            JOIN table_sessions s ON s.id = o.session_id
            WHERE s.restaurant_id <> o.restaurant_id
        ) OR EXISTS (
            SELECT 1 FROM orders o
            JOIN session_participants p ON p.id = o.participant_id
            WHERE p.restaurant_id <> o.restaurant_id
        ) OR EXISTS (
            SELECT 1 FROM bills b
            JOIN table_sessions s ON s.id = b.session_id
            WHERE s.restaurant_id <> b.restaurant_id
        ) OR EXISTS (
            SELECT 1 FROM payments p
            JOIN bills b ON b.id = p.bill_id
            WHERE b.restaurant_id <> p.restaurant_id
        ) OR EXISTS (
            SELECT 1 FROM service_requests r
            JOIN table_sessions s ON s.id = r.session_id
            WHERE s.restaurant_id <> r.restaurant_id
        ) THEN
            RAISE EXCEPTION 'TableFlow tenant integrity check failed; repair mismatched rows before applying this migration';
        END IF;
    END $$;
    """)

    # Parent keys required by PostgreSQL composite foreign keys.
    op.create_unique_constraint(
        "uq_dining_table_id_restaurant", "dining_tables", ["id", "restaurant_id"]
    )
    op.create_unique_constraint(
        "uq_table_session_id_restaurant", "table_sessions", ["id", "restaurant_id"]
    )
    op.create_unique_constraint(
        "uq_participant_id_restaurant", "session_participants", ["id", "restaurant_id"]
    )
    op.create_unique_constraint(
        "uq_menu_category_id_restaurant", "menu_categories", ["id", "restaurant_id"]
    )
    op.create_unique_constraint(
        "uq_order_id_restaurant", "orders", ["id", "restaurant_id"]
    )
    op.create_unique_constraint(
        "uq_bill_id_restaurant", "bills", ["id", "restaurant_id"]
    )

    # These constraints prevent cross-restaurant references even if an API
    # endpoint accidentally omits a tenant filter.
    op.create_foreign_key(
        "fk_table_session_table_restaurant", "table_sessions", "dining_tables",
        ["table_id", "restaurant_id"], ["id", "restaurant_id"]
    )
    op.create_foreign_key(
        "fk_participant_session_restaurant", "session_participants", "table_sessions",
        ["session_id", "restaurant_id"], ["id", "restaurant_id"]
    )
    op.create_foreign_key(
        "fk_menu_item_category_restaurant", "menu_items", "menu_categories",
        ["category_id", "restaurant_id"], ["id", "restaurant_id"]
    )
    op.create_foreign_key(
        "fk_order_session_restaurant", "orders", "table_sessions",
        ["session_id", "restaurant_id"], ["id", "restaurant_id"]
    )
    op.create_foreign_key(
        "fk_order_participant_restaurant", "orders", "session_participants",
        ["participant_id", "restaurant_id"], ["id", "restaurant_id"]
    )
    op.create_foreign_key(
        "fk_bill_session_restaurant", "bills", "table_sessions",
        ["session_id", "restaurant_id"], ["id", "restaurant_id"]
    )
    op.create_foreign_key(
        "fk_payment_bill_restaurant", "payments", "bills",
        ["bill_id", "restaurant_id"], ["id", "restaurant_id"]
    )
    op.create_foreign_key(
        "fk_service_request_session_restaurant", "service_requests", "table_sessions",
        ["session_id", "restaurant_id"], ["id", "restaurant_id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_service_request_session_restaurant", "service_requests", type_="foreignkey")
    op.drop_constraint("fk_payment_bill_restaurant", "payments", type_="foreignkey")
    op.drop_constraint("fk_bill_session_restaurant", "bills", type_="foreignkey")
    op.drop_constraint("fk_order_participant_restaurant", "orders", type_="foreignkey")
    op.drop_constraint("fk_order_session_restaurant", "orders", type_="foreignkey")
    op.drop_constraint("fk_menu_item_category_restaurant", "menu_items", type_="foreignkey")
    op.drop_constraint("fk_participant_session_restaurant", "session_participants", type_="foreignkey")
    op.drop_constraint("fk_table_session_table_restaurant", "table_sessions", type_="foreignkey")
    op.drop_constraint("uq_bill_id_restaurant", "bills", type_="unique")
    op.drop_constraint("uq_order_id_restaurant", "orders", type_="unique")
    op.drop_constraint("uq_menu_category_id_restaurant", "menu_categories", type_="unique")
    op.drop_constraint("uq_participant_id_restaurant", "session_participants", type_="unique")
    op.drop_constraint("uq_table_session_id_restaurant", "table_sessions", type_="unique")
    op.drop_constraint("uq_dining_table_id_restaurant", "dining_tables", type_="unique")
