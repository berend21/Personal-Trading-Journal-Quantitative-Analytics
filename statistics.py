
def safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def roundit(value, digits=2):
    return round(safe_float(value), digits)


def percentage(numerator, denominator, digits=1):
    if not denominator:
        return 0.0
    return round((numerator / denominator) * 100, digits)


def calculate_streaks(rr_values):

    max_win_streak = 0
    max_loss_streak = 0

    current_win = 0
    current_loss = 0

    for rr in rr_values:
        rr = safe_float(rr)

        if rr > 0:
            current_win += 1
            current_loss = 0
        elif rr < 0:
            current_loss += 1
            current_win = 0
        else:
            current_win = 0
            current_loss = 0

        max_win_streak = max(max_win_streak, current_win)
        max_loss_streak = max(max_loss_streak, current_loss)

    return max_win_streak, max_loss_streak


def calculate_drawdown(rr_values):

    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    max_drawdown_pct = 0.0

    equity_curve = []
    drawdown_curve = []

    for rr in rr_values:
        equity += safe_float(rr)
        peak = max(peak, equity)

        drawdown = equity - peak

        if drawdown < max_drawdown:
            max_drawdown = drawdown

        if peak > 0:
            dd_pct = abs(drawdown) / peak * 100
            max_drawdown_pct = max(max_drawdown_pct, dd_pct)

        equity_curve.append(round(equity, 4))
        drawdown_curve.append(round(drawdown, 4))

    return (
        round(max_drawdown, 2),
        round(max_drawdown_pct, 2),
        equity_curve,
        drawdown_curve,
    )

