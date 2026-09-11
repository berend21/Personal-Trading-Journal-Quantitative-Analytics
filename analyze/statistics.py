
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
    current_drawdown = 0.0

    equity_curve = []
    drawdown_curve = []

    max_drawdown_duration = 0
    current_drawdown_duration = 0

    recovery_trades = None
    recovery_counter = None

    for rr in rr_values:
        rr = safe_float(rr)

        equity += rr

        # New equity high
        if equity >= peak:
            peak = equity

            # A drawdown has been fully recovered.
            if recovery_counter is not None:
                recovery_trades = recovery_counter + 1
                recovery_counter = None

            current_drawdown_duration = 0

        else:
            # Still below the previous equity peak.
            current_drawdown_duration += 1

            max_drawdown_duration = max(
                max_drawdown_duration,
                current_drawdown_duration,
            )

            if recovery_counter is None:
                recovery_counter = 0

            recovery_counter += 1

        drawdown = equity - peak

        current_drawdown = drawdown

        if drawdown < max_drawdown:
            max_drawdown = drawdown

        equity_curve.append(round(equity, 4))
        drawdown_curve.append(round(drawdown, 4))

    return {
        "max_drawdown": round(max_drawdown, 2),
        "current_drawdown": round(current_drawdown, 2),
        "max_drawdown_duration": max_drawdown_duration,
        "recovery_trades": recovery_trades,
        "equity_curve": equity_curve,
        "drawdown_curve": drawdown_curve,
    }
