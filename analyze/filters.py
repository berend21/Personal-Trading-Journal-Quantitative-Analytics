from datetime import timedelta

VALID_PERIODS = {
    "monthly",
    "last_month",
    "7d",
    "30d",
    "90d",
    "ytd",
    "all",
    "custom",
}

def date_range(
    period,
    now,
    custom_start=None,
    custom_end=None,
):
    today_end = now.replace(
        hour=23,
        minute=59,
        second=59,
        microsecond=999999,
    )

    if period == "7d":
        start = (now - timedelta(days=6)).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        return start, today_end

    if period == "30d":
        start = (now - timedelta(days=29)).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        return start, today_end

    if period == "90d":
        start = (now - timedelta(days=89)).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        return start, today_end

    if period == "monthly":
        start = now.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        return start, today_end


    if period == "last_month":
        this_month_start = now.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        last_month_end = (
            this_month_start - timedelta(microseconds=1)
        )

        last_month_start = last_month_end.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        return last_month_start, last_month_end

    if period == "ytd":
        start = now.replace(
            month=1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        return start, today_end

    if period == "custom":
        return custom_start, custom_end

    return None, None


def build_filter(
    period,
    now,
    date_field="close_time",
    custom_start=None,
    custom_end=None,
):

    if date_field not in {"open_time", "close_time"}:
        raise ValueError(
            f"Invalid analytics date field: {date_field}"
        )

    conditions = ["parent_id IS NULL"]
    params = []

    start_date, end_date = date_range(
        period,
        now,
        custom_start=custom_start,
        custom_end=custom_end,
    )

    if start_date and end_date:
        conditions.append(
            f"{date_field} >= ? AND {date_field} <= ?"
        )

        params.extend([
            start_date.strftime("%Y-%m-%d %H:%M:%S"),
            end_date.strftime("%Y-%m-%d %H:%M:%S"),
        ])

    return " AND ".join(conditions), params
