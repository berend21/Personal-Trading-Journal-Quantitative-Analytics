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
            "HTF",
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
            "MTF",
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


class TestRecalculateParentAccountingInvariants:

    def test_accounting_conservation(self, test_db):
        parent_id = create_parent(test_db, initial_risk=2.0)

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
            risk_action="OPEN",
        )

        create_child(
            test_db,
            parent_id,
            risk=1.0,
            risk_action="CLOSE",
            rr=2.0,
            close_time="2026-08-31 10:00:00",
        )

        result = recalculate_parent(test_db, parent_id)

        assert result["total_committed_risk"] == pytest.approx(3.25)
        assert result["added_risk"] == pytest.approx(1.25)
        assert result["closed_risk"] == pytest.approx(1.0)
        assert result["current_risk"] == pytest.approx(2.25)

        assert (
            result["current_risk"]
            == pytest.approx(
                result["total_committed_risk"]
                - result["closed_risk"]
            )
        )

    def test_multiple_opens_and_closes_conserve_risk(self, test_db):
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
            risk=0.25,
            risk_action="CLOSE",
            rr=2.0,
            close_time="2026-08-31 10:00:00",
        )

        create_child(
            test_db,
            parent_id,
            risk=0.75,
            risk_action="OPEN",
        )

        create_child(
            test_db,
            parent_id,
            risk=0.5,
            risk_action="CLOSE",
            rr=-1.0,
            close_time="2026-08-31 11:00:00",
        )

        result = recalculate_parent(test_db, parent_id)

        # 1.0 initial + 0.5 + 0.75 added = 2.25 committed
        assert result["total_committed_risk"] == pytest.approx(2.25)
        assert result["added_risk"] == pytest.approx(1.25)

        # 0.25 + 0.5 closed = 0.75
        assert result["closed_risk"] == pytest.approx(0.75)

        # 2.25 - 0.75 = 1.50 remaining
        assert result["current_risk"] == pytest.approx(1.50)

        # 0.25 * 2 + 0.5 * -1 = 0
        assert result["realized_r"] == pytest.approx(0.0)

    def test_realized_r_is_independent_of_remaining_risk(self, test_db):
        parent_id = create_parent(test_db, initial_risk=2.0)

        create_child(
            test_db,
            parent_id,
            risk=0.5,
            risk_action="CLOSE",
            rr=4.0,
            close_time="2026-08-31 10:00:00",
        )

        result = recalculate_parent(test_db, parent_id)

        assert result["closed_risk"] == pytest.approx(0.5)
        assert result["current_risk"] == pytest.approx(1.5)

        # Realized R comes only from the closed portion.
        assert result["realized_r"] == pytest.approx(1.0)

    def test_fractional_risk_is_accounted_for_exactly(self, test_db):
        parent_id = create_parent(
            test_db,
            initial_risk=1.0,
        )

        create_child(
            test_db,
            parent_id,
            risk=0.125,
            risk_action="OPEN",
        )

        create_child(
            test_db,
            parent_id,
            risk=0.375,
            risk_action="CLOSE",
            rr=2.5,
            close_time="2026-08-31 10:00:00",
        )

        result = recalculate_parent(test_db, parent_id)

        assert result["total_committed_risk"] == pytest.approx(1.125)
        assert result["added_risk"] == pytest.approx(0.125)
        assert result["closed_risk"] == pytest.approx(0.375)
        assert result["current_risk"] == pytest.approx(0.75)
        assert result["realized_r"] == pytest.approx(0.8333333333)

    def test_breakeven_close_reduces_risk_without_realizing_r(self, test_db):
        parent_id = create_parent(test_db, initial_risk=1.0)

        create_child(
            test_db,
            parent_id,
            risk=0.4,
            risk_action="CLOSE",
            rr=0.0,
            close_time="2026-08-31 10:00:00",
        )

        result = recalculate_parent(test_db, parent_id)

        assert result["closed_risk"] == pytest.approx(0.4)
        assert result["current_risk"] == pytest.approx(0.6)
        assert result["realized_r"] == pytest.approx(0.0)
        assert result["status"] == "OPEN"

    def test_losing_partial_close_reduces_realized_r(self, test_db):
        parent_id = create_parent(test_db, initial_risk=1.0)

        create_child(
            test_db,
            parent_id,
            risk=0.25,
            risk_action="CLOSE",
            rr=-2.0,
            close_time="2026-08-31 10:00:00",
        )

        result = recalculate_parent(test_db, parent_id)

        assert result["closed_risk"] == pytest.approx(0.25)
        assert result["current_risk"] == pytest.approx(0.75)
        assert result["realized_r"] == pytest.approx(-0.5)

    def test_exact_close_zeroes_current_risk(self, test_db):
        parent_id = create_parent(test_db, initial_risk=1.0)

        create_child(
            test_db,
            parent_id,
            risk=0.4,
            risk_action="OPEN",
        )

        create_child(
            test_db,
            parent_id,
            risk=1.4,
            risk_action="CLOSE",
            rr=1.5,
            close_time="2026-08-31 12:00:00",
        )

        result = recalculate_parent(test_db, parent_id)

        assert result["total_committed_risk"] == pytest.approx(1.4)
        assert result["closed_risk"] == pytest.approx(1.4)
        assert result["current_risk"] == pytest.approx(0.0)
        assert result["status"] == "CLOSED"
        assert result["realized_r"] == pytest.approx(1.5)



    def test_over_close_is_rejected_after_added_risk_is_accounted_for(
        self,
        test_db,
    ):
        parent_id = create_parent(test_db, initial_risk=1.0)

        create_child(
            test_db,
            parent_id,
            risk=0.5,
            risk_action="OPEN",
        )

        # 1.5 committed risk, so closing exactly 1.5 is valid.
        create_child(
            test_db,
            parent_id,
            risk=1.500001,
            risk_action="CLOSE",
            rr=1.0,
            close_time="2026-08-31 12:00:00",
        )

        with pytest.raises(ValueError, match="closed risk"):
            recalculate_parent(test_db, parent_id)

    def test_child_row_order_does_not_change_accounting(self, test_db):
        parent_a = create_parent(test_db, initial_risk=1.0)
        parent_b = create_parent(test_db, initial_risk=1.0)

        children = [
            (0.5, "OPEN", None),
            (0.25, "CLOSE", 2.0),
            (0.75, "OPEN", None),
            (0.5, "CLOSE", -1.0),
        ]

        for risk, action, rr in children:
            create_child(
                test_db,
                parent_a,
                risk=risk,
                risk_action=action,
                rr=rr,
                close_time=(
                    "2026-08-31 10:00:00"
                    if action == "CLOSE"
                    else None
                ),
            )

        for risk, action, rr in reversed(children):
            create_child(
                test_db,
                parent_b,
                risk=risk,
                risk_action=action,
                rr=rr,
                close_time=(
                    "2026-08-31 10:00:00"
                    if action == "CLOSE"
                    else None
                ),
            )

        result_a = recalculate_parent(test_db, parent_a)
        result_b = recalculate_parent(test_db, parent_b)

        assert result_a["total_committed_risk"] == pytest.approx(
            result_b["total_committed_risk"]
        )
        assert result_a["added_risk"] == pytest.approx(
            result_b["added_risk"]
        )
        assert result_a["closed_risk"] == pytest.approx(
            result_b["closed_risk"]
        )
        assert result_a["current_risk"] == pytest.approx(
            result_b["current_risk"]
        )
        assert result_a["realized_r"] == pytest.approx(
            result_b["realized_r"]
        )
        assert result_a["status"] == result_b["status"]


    @pytest.mark.parametrize(
        "initial_risk,opens,closes,expected_committed,expected_closed,expected_current,expected_realized",
        [
            # 2R on 0.25 / 1.0 = 0.5R
            (1.0, [], [(0.25, 2.0)], 1.0, 0.25, 0.75, 0.5),

            # 2R on 0.50 / 1.0 = 1.0R
            (1.0, [], [(0.50, 2.0)], 1.0, 0.50, 0.50, 1.0),

            # 2R on 0.25 / 1.5 = 0.333333R
            (1.0, [(0.5, None)], [(0.25, 2.0)], 1.5, 0.25, 1.25, 0.3333333333),

            # 1R on 1.5 / 1.5 = 1.0R
            (1.0, [(0.5, None)], [(1.5, 1.0)], 1.5, 1.5, 0.0, 1.0),

            # -2R on 0.5 / 2.0 = -0.5R
            (2.0, [], [(0.5, -2.0)], 2.0, 0.5, 1.5, -0.5),

            # 2.5R on 0.375 / 1.125 = 0.833333R
            (1.0, [(0.125, None)], [(0.375, 2.5)], 1.125, 0.375, 0.75, 0.8333333333),
        ],
    )
    def test_partial_accounting_matrix(
        self,
        test_db,
        initial_risk,
        opens,
        closes,
        expected_committed,
        expected_closed,
        expected_current,
        expected_realized,
    ):
        parent_id = create_parent(
            test_db,
            initial_risk=initial_risk,
        )

        for risk, rr in opens:
            create_child(
                test_db,
                parent_id,
                risk=risk,
                risk_action="OPEN",
            )

        for risk, rr in closes:
            create_child(
                test_db,
                parent_id,
                risk=risk,
                risk_action="CLOSE",
                rr=rr,
                close_time="2026-08-31 12:00:00",
            )

        result = recalculate_parent(test_db, parent_id)

        assert result["total_committed_risk"] == pytest.approx(
            expected_committed
        )
        assert result["closed_risk"] == pytest.approx(
            expected_closed
        )
        assert result["current_risk"] == pytest.approx(
            expected_current
        )
        assert result["realized_r"] == pytest.approx(
            expected_realized
        )

        # Core conservation invariant.
        assert result["current_risk"] == pytest.approx(
            result["total_committed_risk"]
            - result["closed_risk"]
        )


    def test_parent_is_recalculated_after_closing_partial(self, authenticated_client,flask_connection):
        parent_id = create_parent(flask_connection, initial_risk=1.0)

        create_child(
            flask_connection,
            parent_id,
            risk=0.4,
            risk_action="CLOSE",
            rr=2.0,
            close_time="2026-08-31 12:00:00",
        )

        result = recalculate_parent(flask_connection, parent_id)

        assert result["current_risk"] == pytest.approx(0.6)
        assert result["closed_risk"] == pytest.approx(0.4)
        assert result["realized_r"] == pytest.approx(0.8)
        assert result["status"] == "OPEN"

        parent = flask_connection.execute(
            "SELECT * FROM trades WHERE id=?",
            (parent_id,),
        ).fetchone()

        assert parent["risk"] == pytest.approx(0.6)
        assert parent["RR"] == pytest.approx(0.8)
        assert parent["status"] == "OPEN"


    def test_parent_is_closed_when_all_risk_is_closed(self, test_db):
        parent_id = create_parent(test_db, initial_risk=1.0)

        create_child(
            test_db,
            parent_id,
            risk=1.0,
            risk_action="CLOSE",
            rr=1.5,
            close_time="2026-08-31 12:00:00",
        )

        result = recalculate_parent(test_db, parent_id)

        assert result["current_risk"] == pytest.approx(0.0)
        assert result["closed_risk"] == pytest.approx(1.0)
        assert result["status"] == "CLOSED"
        assert result["close_time"] == "2026-08-31 12:00:00"

        parent = test_db.execute(
            "SELECT * FROM trades WHERE id=?",
            (parent_id,),
        ).fetchone()

        assert parent["risk"] == pytest.approx(1.0)
        assert parent["status"] == "CLOSED"
        assert parent["close_time"] == "2026-08-31 12:00:00"


    def test_parent_reopens_when_closed_partial_is_changed_to_open(self, test_db,):
        parent_id = create_parent(test_db, initial_risk=1.0)

        child_id = create_child(
            test_db,
            parent_id,
            risk=1.0,
            risk_action="CLOSE",
            rr=1.5,
            close_time="2026-08-31 12:00:00",
        )

        result = recalculate_parent(test_db, parent_id)

        assert result["status"] == "CLOSED"
        assert result["current_risk"] == pytest.approx(0.0)

        test_db.execute(
            """
            UPDATE trades
            SET risk_action='OPEN',
                status='OPEN',
                RR=NULL,
                close_time=NULL
            WHERE id=?
            """,
            (child_id,),
        )
        test_db.commit()

        result = recalculate_parent(test_db, parent_id)

        assert result["status"] == "OPEN"
        assert result["current_risk"] == pytest.approx(2.0)
        assert result["closed_risk"] == pytest.approx(0.0)
        assert result["added_risk"] == pytest.approx(1.0)
        assert result["realized_r"] == pytest.approx(0.0)


    def test_parent_recalculation_uses_latest_close_time(self, test_db):
        parent_id = create_parent(test_db, initial_risk=1.0)

        create_child(
            test_db,
            parent_id,
            risk=0.25,
            risk_action="CLOSE",
            rr=1.0,
            close_time="2026-08-31 10:00:00",
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

        assert result["status"] == "CLOSED"
        assert result["current_risk"] == pytest.approx(0.0)
        assert result["close_time"] == "2026-08-31 12:00:00"


    def test_parent_rr_is_weighted_by_closed_risk(self, test_db):
        parent_id = create_parent(test_db, initial_risk=2.0)

        create_child(
            test_db,
            parent_id,
            risk=0.5,
            risk_action="CLOSE",
            rr=4.0,
            close_time="2026-08-31 10:00:00",
        )

        create_child(
            test_db,
            parent_id,
            risk=1.0,
            risk_action="CLOSE",
            rr=-1.0,
            close_time="2026-08-31 11:00:00",
        )

        result = recalculate_parent(test_db, parent_id)

        # (0.5 * 4) + (1.0 * -1) = 1.0
        assert result["realized_r"] == pytest.approx(0.5)

        # 2.0 initial - 1.5 closed = 0.5 remaining
        assert result["current_risk"] == pytest.approx(0.5)

