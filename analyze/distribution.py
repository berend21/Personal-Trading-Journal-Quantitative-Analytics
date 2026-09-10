from .statistics import safe_float, roundit, percentage


def calculate_r_distribution(rr_values):

    values = [
        safe_float(rr)
        for rr in rr_values
    ]

    if not values:
        return {
            "bins": [],
            "labels": [],
            "counts": [],
            "percentages": [],
            "total": 0,
            "unique_results": 0,
            "positive_results": 0,
            "negative_results": 0,
            "breakeven_results": 0,
            "average_rr": 0.0,
            "median_rr": None,
            "most_common_rr": None,
            "most_common_count": 0,
            "colors": [],
        }

    total = len(values)

    positive_results = sum(
        1 for rr in values
        if rr > 0
    )

    negative_results = sum(
        1 for rr in values
        if rr < 0
    )

    breakeven_results = sum(
        1 for rr in values
        if rr == 0
    )

    buckets = [
        ("-1 to -0.5", lambda rr: -1 <= rr < -0.5),
        ("-0.5 to 0", lambda rr: -0.5 <= rr < 0),
        ("0", lambda rr: rr == 0),
        ("0 to 1", lambda rr: 0 < rr < 1),
        ("1 to 2", lambda rr: 1 <= rr < 2),
        ("2 to 3", lambda rr: 2 <= rr < 3),
        ("3 to 4", lambda rr: 3 <= rr < 4),
        ("4 to 5", lambda rr: 4 <= rr < 5),
        ("5+", lambda rr: rr >= 5),
    ]

    labels = [
        label
        for label, _ in buckets
    ]

    counts = [
        sum(
            1
            for rr in values
            if condition(rr)
        )
        for _, condition in buckets
    ]

    percentages = [
        percentage(count, total, digits=1)
        for count in counts
    ]
    # not used rn since JS overwrites them but well
    colors = [
        "#ef4444",  # -1 to -0.5
        "#ef4444",  # -0.5 to 0
        "#94a3b8",  # 0
        "#f59e0b",  # 0 to 1
        "#22c55e",  # 1 to 2
        "#22c55e",  # 2 to 3
        "#22c55e",  # 3 to 4
        "#16a34a",  # 4 to 5
        "#16a34a", #5+
        
    ]

    ordered = sorted(values)
    n = len(ordered)

    if n % 2 == 1:
        median_rr = ordered[n // 2]
    else:
        median_rr = (
            ordered[n // 2 - 1]
            + ordered[n // 2]
        ) / 2

    rounded_values = [
        roundit(rr, 2)
        for rr in values
    ]

    from collections import Counter

    distribution = Counter(rounded_values)

    most_common_rr, most_common_count = (
        distribution.most_common(1)[0]
    )

    return {
        "bins": labels,
        "labels": labels,
        "counts": counts,
        "percentages": percentages,

        "total": total,
        "unique_results": len(
            set(rounded_values)
        ),

        "positive_results": positive_results,
        "negative_results": negative_results,
        "breakeven_results": breakeven_results,

        "average_rr": roundit(
            sum(values) / total
        ),

        "median_rr": roundit(
            median_rr
        ),

        "most_common_rr": most_common_rr,
        "most_common_count": most_common_count,

        "colors": colors,
    }
