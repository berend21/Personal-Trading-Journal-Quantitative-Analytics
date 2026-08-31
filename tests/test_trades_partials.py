import pytest
from trades import recalculate_parent


def create_parent(conn, initial_risk=1.0):
    cursor = conn.execute(
        """
        INSERT INTO trades (
            symbol,
            type,
            status,
            sort,
            initial_risk,
            risk,
            RR,
            risk_action
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "TEST",
            "TEST",
            "OPEN",
            "LONG",
            initial_risk,
            initial_risk,
            0.0,
            None,
        ),
    )

    conn.commit()

    return cursor.lastrowid


def create_child(
    conn,
    parent_id,
    risk,
    risk_action,
    rr=None,
    close_time=None,
):
    cursor = conn.execute(
        """
        INSERT INTO trades (
            symbol,
            type,
            status,
            sort,
            parent_id,
            risk,
            RR,
            risk_action,
            close_time
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "TEST",
            "TEST",
            "OPEN",
            "LONG",
            parent_id,
            risk,
            rr,
            risk_action,
            close_time,
        ),
    )

    conn.commit()

    return cursor.lastrowid


class TestRecalculateParent:

    def test_parent_without_children_uses_initial_risk(self, test_db):
        parent_id = create_parent(test_db, initial_risk=1.0)

        result = recalculate_parent(test_db, parent_id)

        assert result["current_risk"] == pytest.approx(1.0)
        assert result["total_committed_risk"] == pytest.approx(1.0)
        assert result["closed_risk"] == pytest.approx(0.0)
        assert result["added_risk"] == pytest.approx(0.0)
        assert result["realized_r"] == pytest.approx(0.0)
        assert result["status"] == "OPEN"
        assert result["close_time"] is None

    def test_added_risk_increases_current_risk(self, test_db):
        parent_id = create_parent(test_db, initial_risk=1.0)

        create_child(
            test_db,
            parent_id,
            risk=0.5,
            risk_action="OPEN",
        )

        result = recalculate_parent(test_db, parent_id)

        assert result["total_committed_risk"] == pytest.approx(1.5)
        assert result["added_risk"] == pytest.approx(0.5)
        assert result["closed_risk"] == pytest.approx(0.0)
        assert result["current_risk"] == pytest.approx(1.5)

    def test_partial_close_reduces_current_risk(self, test_db):
        parent_id = create_parent(test_db, initial_risk=1.0)

        create_child(
            test_db,
            parent_id,
            risk=0.5,
            risk_action="CLOSE",
            rr=2.0,
            close_time="2026-08-31 10:00:00",
        )

        result = recalculate_parent(test_db, parent_id)

        assert result["total_committed_risk"] == pytest.approx(1.0)
        assert result["closed_risk"] == pytest.approx(0.5)
        assert result["current_risk"] == pytest.approx(0.5)
        assert result["realized_r"] == pytest.approx(1.0)

    def test_multiple_partial_closes_accumulate(self, test_db):
        parent_id = create_parent(test_db, initial_risk=1.0)

        create_child(
            test_db,
            parent_id,
            risk=0.25,
            risk_action="CLOSE",
            rr=2.0,
            close_time="2026-08-31 10:00:00",
        )

        create_child(
            test_db,
            parent_id,
            risk=0.25,
            risk_action="CLOSE",
            rr=1.0,
            close_time="2026-08-31 11:00:00",
        )

        result = recalculate_parent(test_db, parent_id)

        assert result["closed_risk"] == pytest.approx(0.5)
        assert result["current_risk"] == pytest.approx(0.5)

        # 0.25 * 2R + 0.25 * 1R = 0.75R
        assert result["realized_r"] == pytest.approx(0.75)

    def test_added_risk_and_partial_close(self, test_db):
        parent_id = create_parent(test_db, initial_risk=1.0)

        create_child(
            test_db,
            parent_id,
            risk=0.5,
            risk_action="OPEN",
        )

        create_child(
            test_db,
            parent_id,
            risk=0.75,
            risk_action="CLOSE",
            rr=2.0,
            close_time="2026-08-31 12:00:00",
        )

        result = recalculate_parent(test_db, parent_id)

        assert result["total_committed_risk"] == pytest.approx(1.5)
        assert result["added_risk"] == pytest.approx(0.5)
        assert result["closed_risk"] == pytest.approx(0.75)
        assert result["current_risk"] == pytest.approx(0.75)
        assert result["realized_r"] == pytest.approx(1.5)

    def test_cannot_close_more_risk_than_committed(self, test_db):
        parent_id = create_parent(test_db, initial_risk=1.0)

        create_child(
            test_db,
            parent_id,
            risk=1.5,
            risk_action="CLOSE",
            rr=2.0,
            close_time="2026-08-31 12:00:00",
        )

        with pytest.raises(ValueError, match="closed risk"):
            recalculate_parent(test_db, parent_id)

    def test_missing_parent_returns_none(self, test_db):
        result = recalculate_parent(test_db, 999999)

        assert result is None

    def test_partial_close_updates_parent_database_row(self, test_db):
        parent_id = create_parent(test_db, initial_risk=1.0)

        create_child(
            test_db,
            parent_id,
            risk=0.5,
            risk_action="CLOSE",
            rr=2.0,
            close_time="2026-08-31 12:00:00",
        )

        recalculate_parent(test_db, parent_id)

        parent = test_db.execute(
            "SELECT * FROM trades WHERE id=?",
            (parent_id,),
        ).fetchone()

        assert parent["risk"] == pytest.approx(0.5)
        assert parent["RR"] == pytest.approx(1.0)
        assert parent["status"] == "OPEN"


    def test_added_risk_updates_parent_database_row(self, test_db):
        parent_id = create_parent(test_db, initial_risk=1.0)

        create_child(
            test_db,
            parent_id,
            risk=0.5,
            risk_action="OPEN",
        )

        recalculate_parent(test_db, parent_id)

        parent = test_db.execute(
            "SELECT * FROM trades WHERE id=?",
            (parent_id,),
        ).fetchone()

        assert parent["risk"] == pytest.approx(1.5)
        assert parent["status"] == "OPEN"


    def test_closing_entire_position_updates_parent_status(self, test_db):
        parent_id = create_parent(test_db, initial_risk=1.0)

        create_child(
            test_db,
            parent_id,
            risk=1.0,
            risk_action="CLOSE",
            rr=2.0,
            close_time="2026-08-31 12:00:00",
        )

        recalculate_parent(test_db, parent_id)

        parent = test_db.execute(
            "SELECT * FROM trades WHERE id=?",
            (parent_id,),
        ).fetchone()

        assert parent["risk"] == pytest.approx(0.0)
        assert parent["RR"] == pytest.approx(2.0)
        assert parent["status"] == "CLOSED"
        assert parent["close_time"] == "2026-08-31 12:00:00"
