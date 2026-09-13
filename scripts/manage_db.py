# ruff: noqa
import argparse

from psycopg import sql

from app.db import get_conn


def add_subscriber(phone: str, plan: str, monthly_token_limit: int) -> None:
    """Add or update a subscriber in the database."""
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO subscribers (phone, plan, monthly_token_limit, is_active)
            VALUES (%s, %s, %s, TRUE)
            ON CONFLICT (phone) DO UPDATE SET plan=EXCLUDED.plan, monthly_token_limit=EXCLUDED.monthly_token_limit, is_active=TRUE
            """,
            (phone, plan, monthly_token_limit),
        )
    print(f"✅ Added or updated subscriber: {phone}")


def activate_subscriber(phone: str) -> None:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT 1 FROM subscribers WHERE phone=%s",
            (phone,),
        )
        if cur.fetchone() is None:
            print(f"❌ Subscriber not found: {phone}")
            return
        conn.execute(
            "UPDATE subscribers SET is_active=TRUE WHERE phone=%s",
            (phone,),
        )
    print(f"✅ Activated subscriber: {phone}")


def delete_subscriber(phone: str) -> None:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT 1 FROM subscribers WHERE phone=%s",
            (phone,),
        )
        if cur.fetchone() is None:
            print(f"❌ Subscriber not found: {phone}")
            return
        conn.execute(
            "DELETE FROM usage_log WHERE phone_fk=%s",
            (phone,),
        )
        conn.execute(
            "DELETE FROM subscribers WHERE phone=%s",
            (phone,),
        )
    print(f"🗑️ Deleted subscriber and all related usage: {phone}")


def deactivate_subscriber(phone: str) -> None:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT 1 FROM subscribers WHERE phone=%s",
            (phone,),
        )
        if cur.fetchone() is None:
            print(f"❌ Subscriber not found: {phone}")
            return
        conn.execute(
            "UPDATE subscribers SET is_active=FALSE WHERE phone=%s",
            (phone,),
        )
    print(f"🚫 Deactivated subscriber: {phone}")


def get_subscriber_info(phone: str) -> None:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT phone, plan, monthly_token_limit, is_active, created_at FROM subscribers WHERE phone=%s",
            (phone,),
        )
        row = cur.fetchone()
        if row:
            print(f"📄 Subscriber info for {phone}:")
            print(f"  Plan: {row[1]}")
            print(f"  Monthly Token Limit: {row[2]}")
            print(f"  Is Active: {row[3]}")
            print(f"  Created At: {row[4]}")
        else:
            print(f"❌ Subscriber not found: {phone}")


def list_subscribers() -> None:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT phone, plan, monthly_token_limit, is_active FROM subscribers",
        )
        for row in cur.fetchall():
            print(row)


def clear_test_subscribers() -> None:
    with get_conn() as conn:
        cur = conn.execute("SELECT phone FROM subscribers")
        test_phones = [
            row[0] for row in cur.fetchall() if row[0] and row[0].startswith("1555")
        ]
        if not test_phones:
            print("✅ No test subscribers to delete.")
            return
        # Dynamic placeholders using psycopg.sql
        placeholders = sql.SQL(",").join(sql.Placeholder() * len(test_phones))
        # Delete usage_log entries
        conn.execute(
            sql.SQL("DELETE FROM usage_log WHERE phone_fk IN ({})").format(
                placeholders,
            ),
            test_phones,
        )
        # Delete subscribers
        conn.execute(
            sql.SQL("DELETE FROM subscribers WHERE phone IN ({})").format(placeholders),
            test_phones,
        )
        print(f"🧹 Deleted {len(test_phones)} test subscribers and related usage logs.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manual DB Admin for WhatsApp Bot")
    subparsers = parser.add_subparsers(dest="command")

    add = subparsers.add_parser("add")
    add.add_argument("phone")
    add.add_argument("plan")
    add.add_argument("monthly_token_limit", type=int)

    activate = subparsers.add_parser("activate")
    activate.add_argument("phone")

    delete = subparsers.add_parser("delete")
    delete.add_argument("phone")

    deactivate = subparsers.add_parser("deactivate")
    deactivate.add_argument("phone")

    info = subparsers.add_parser("info")
    info.add_argument("phone")

    list_all = subparsers.add_parser("list")

    clear = subparsers.add_parser("clear_tests")

    args = parser.parse_args()

    if args.command == "add":
        add_subscriber(args.phone, args.plan, args.monthly_token_limit)
    elif args.command == "deactivate":
        deactivate_subscriber(args.phone)
    elif args.command == "list":
        list_subscribers()
    elif args.command == "info":
        get_subscriber_info(args.phone)
    elif args.command == "clear_tests":
        clear_test_subscribers()
    elif args.command == "activate":
        activate_subscriber(args.phone)
    elif args.command == "delete":
        delete_subscriber(args.phone)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
