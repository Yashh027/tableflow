"""enforce tenant consistency across order and billing items

Revision ID: c175f3edd496
Revises: c4f19a72d8e1
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c175f3edd496"
down_revision: Union[str, Sequence[str], None] = "c4f19a72d8e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Preflight: do not silently repair or discard inconsistent historical data.
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            JOIN menu_items mi ON mi.id = oi.menu_item_id
            WHERE mi.restaurant_id <> o.restaurant_id
               OR oi.order_id IS NULL
        ) THEN
            RAISE EXCEPTION
                'Tenant migration blocked: order_items reference a menu item belonging to another restaurant';
        END IF;

        IF EXISTS (
            SELECT 1
            FROM bill_items bi
            JOIN bills b ON b.id = bi.bill_id
            JOIN order_items oi ON oi.id = bi.order_item_id
            JOIN orders o ON o.id = oi.order_id
            WHERE b.restaurant_id <> o.restaurant_id
               OR b.session_id <> o.session_id
        ) THEN
            RAISE EXCEPTION
                'Tenant migration blocked: bill_items reference an order item from another restaurant or session';
        END IF;

        IF EXISTS (
            SELECT 1
            FROM service_requests sr
            JOIN session_participants sp ON sp.id = sr.participant_id
            WHERE sr.participant_id IS NOT NULL
              AND (
                  sr.restaurant_id <> sp.restaurant_id
                  OR sr.session_id <> sp.session_id
              )
        ) THEN
            RAISE EXCEPTION
                'Tenant migration blocked: service_requests reference a participant from another restaurant or session';
        END IF;
    END $$;
    """)

    # Add nullable columns first so existing records can be safely backfilled.
    op.add_column(
        "order_items",
        sa.Column("restaurant_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "order_items",
        sa.Column("session_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "bill_items",
        sa.Column("restaurant_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "bill_items",
        sa.Column("session_id", sa.Uuid(), nullable=True),
    )

    # Derive ownership from the authoritative parent records.
    op.execute("""
        UPDATE order_items oi
        SET restaurant_id = o.restaurant_id,
            session_id = o.session_id
        FROM orders o
        WHERE o.id = oi.order_id;
    """)

    op.execute("""
        UPDATE bill_items bi
        SET restaurant_id = b.restaurant_id,
            session_id = b.session_id
        FROM bills b
        WHERE b.id = bi.bill_id;
    """)

    # Verify that every row was backfilled before enforcing NOT NULL.
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1 FROM order_items
            WHERE restaurant_id IS NULL OR session_id IS NULL
        ) THEN
            RAISE EXCEPTION
                'Tenant migration blocked: one or more order_items could not be backfilled';
        END IF;

        IF EXISTS (
            SELECT 1 FROM bill_items
            WHERE restaurant_id IS NULL OR session_id IS NULL
        ) THEN
            RAISE EXCEPTION
                'Tenant migration blocked: one or more bill_items could not be backfilled';
        END IF;
    END $$;
    """)

    op.alter_column("order_items", "restaurant_id", nullable=False)
    op.alter_column("order_items", "session_id", nullable=False)
    op.alter_column("bill_items", "restaurant_id", nullable=False)
    op.alter_column("bill_items", "session_id", nullable=False)

    # Match the indexes declared by the SQLAlchemy models.
    op.create_index(
        "ix_order_items_restaurant_id",
        "order_items",
        ["restaurant_id"],
    )
    op.create_index(
        "ix_order_items_session_id",
        "order_items",
        ["session_id"],
    )
    op.create_index(
        "ix_bill_items_restaurant_id",
        "bill_items",
        ["restaurant_id"],
    )
    op.create_index(
        "ix_bill_items_session_id",
        "bill_items",
        ["session_id"],
    )

    # Restaurant ownership foreign keys for the new columns.
    op.create_foreign_key(
        "fk_order_items_restaurant_id_restaurants",
        "order_items",
        "restaurants",
        ["restaurant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_bill_items_restaurant_id_restaurants",
        "bill_items",
        "restaurants",
        ["restaurant_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Additional candidate keys required by the composite foreign keys.
    op.create_unique_constraint(
        "uq_menu_item_id_restaurant",
        "menu_items",
        ["id", "restaurant_id"],
    )
    op.create_unique_constraint(
        "uq_order_id_session_restaurant",
        "orders",
        ["id", "session_id", "restaurant_id"],
    )
    op.create_unique_constraint(
        "uq_order_item_id_session_restaurant",
        "order_items",
        ["id", "session_id", "restaurant_id"],
    )
    op.create_unique_constraint(
        "uq_bill_id_session_restaurant",
        "bills",
        ["id", "session_id", "restaurant_id"],
    )
    op.create_unique_constraint(
        "uq_participant_id_session_restaurant",
        "session_participants",
        ["id", "session_id", "restaurant_id"],
    )

    # An order item must belong to both the same order and restaurant.
    op.create_foreign_key(
        "fk_order_item_order_session_restaurant",
        "order_items",
        "orders",
        ["order_id", "session_id", "restaurant_id"],
        ["id", "session_id", "restaurant_id"],
    )
    op.create_foreign_key(
        "fk_order_item_menu_restaurant",
        "order_items",
        "menu_items",
        ["menu_item_id", "restaurant_id"],
        ["id", "restaurant_id"],
    )

    # A bill item must reference a bill and order item from the same session
    # and restaurant.
    op.create_foreign_key(
        "fk_bill_item_bill_session_restaurant",
        "bill_items",
        "bills",
        ["bill_id", "session_id", "restaurant_id"],
        ["id", "session_id", "restaurant_id"],
    )
    op.create_foreign_key(
        "fk_bill_item_order_item_session_restaurant",
        "bill_items",
        "order_items",
        ["order_item_id", "session_id", "restaurant_id"],
        ["id", "session_id", "restaurant_id"],
    )

    # A service request participant must belong to the same session and tenant.
    op.create_foreign_key(
        "fk_service_request_participant_session_restaurant",
        "service_requests",
        "session_participants",
        ["participant_id", "session_id", "restaurant_id"],
        ["id", "session_id", "restaurant_id"],
    )


def downgrade() -> None:
    # Drop dependent foreign keys before their candidate keys.
    op.drop_constraint(
        "fk_service_request_participant_session_restaurant",
        "service_requests",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_bill_item_order_item_session_restaurant",
        "bill_items",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_bill_item_bill_session_restaurant",
        "bill_items",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_order_item_menu_restaurant",
        "order_items",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_order_item_order_session_restaurant",
        "order_items",
        type_="foreignkey",
    )

    op.drop_constraint(
        "uq_participant_id_session_restaurant",
        "session_participants",
        type_="unique",
    )
    op.drop_constraint(
        "uq_bill_id_session_restaurant",
        "bills",
        type_="unique",
    )
    op.drop_constraint(
        "uq_order_item_id_session_restaurant",
        "order_items",
        type_="unique",
    )
    op.drop_constraint(
        "uq_order_id_session_restaurant",
        "orders",
        type_="unique",
    )
    op.drop_constraint(
        "uq_menu_item_id_restaurant",
        "menu_items",
        type_="unique",
    )

    op.drop_constraint(
        "fk_bill_items_restaurant_id_restaurants",
        "bill_items",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_order_items_restaurant_id_restaurants",
        "order_items",
        type_="foreignkey",
    )

    op.drop_index("ix_bill_items_session_id", table_name="bill_items")
    op.drop_index("ix_bill_items_restaurant_id", table_name="bill_items")
    op.drop_index("ix_order_items_session_id", table_name="order_items")
    op.drop_index("ix_order_items_restaurant_id", table_name="order_items")

    op.drop_column("bill_items", "session_id")
    op.drop_column("bill_items", "restaurant_id")
    op.drop_column("order_items", "session_id")
    op.drop_column("order_items", "restaurant_id")
