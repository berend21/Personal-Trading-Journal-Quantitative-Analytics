import statistics 
import math
from analyze.expectancy import calculate_expectancy

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



def calculate_profit_factor(gross_profit, gross_loss):
    gross_profit = safe_float(gross_profit)
    gross_loss = safe_float(gross_loss)

    if gross_loss <= 0:
        return None

    return round(gross_profit / gross_loss, 2)

def calculate_median(values):

    if not values:
        return None

    return statistics.median(values)

def calculate_standard_deviation(values):

    if len(values) < 2:
        return 0.0

    mean = sum(values) / len(values)

    variance = sum(
        (value - mean) ** 2
        for value in values
    ) / (len(values) - 1)

    return round(math.sqrt(variance), 2)

def calculate_payoff_ratio(average_win, average_loss):

    if average_win is None or average_loss is None:
        return None

    if average_loss >= 0:
        return None

    return round(
        average_win / abs(average_loss),
        2,
    )
def calculate_win_rate(wins, total):
    if total <= 0:
        return 0.0

    return round((wins / total) * 100, 2)
def calculate_trade_statistics(rr_sequence):
    if not rr_sequence:
        return {
            "closed_count": 0,
            "win_count": 0,
            "loss_count": 0,
            "breakeven_count": 0,
            "total_rr": 0.0,
            "average_rr": 0.0,
            "highest_rr": None,
            "lowest_rr": None,
            "average_win": 0.0,
            "average_loss": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "win_rate": 0.0,
            "loss_rate": 0.0,
            "breakeven_rate": 0.0,
            "profit_factor": None,
            "payoff_ratio": None,
            "median_rr": None,
            "expectancy": 0.0,
            "rr_stddev": 0.0,
        }

    wins = [
        rr for rr in rr_sequence
        if rr > 0
    ]

    losses = [
        rr for rr in rr_sequence
        if rr < 0
    ]

    breakevens = [
        rr for rr in rr_sequence
        if rr == 0
    ]

    closed_count = len(rr_sequence)

    gross_profit = sum(wins)
    gross_loss = sum(
        abs(rr)
        for rr in losses
    )

    average_win = (
        sum(wins) / len(wins)
        if wins
        else 0.0
    )

    average_loss = (
        sum(losses) / len(losses)
        if losses
        else 0.0
    )

    total_rr = sum(rr_sequence)

    average_rr = (
        total_rr / closed_count
        if closed_count
        else 0.0
    )

    expectancy = calculate_expectancy(
        rr_sequence
    )

    return {
        "closed_count": closed_count,

        "win_count": len(wins),
        "loss_count": len(losses),
        "breakeven_count": len(breakevens),

        "total_rr": roundit(total_rr),
        "average_rr": roundit(average_rr),

        "highest_rr": roundit(
            max(rr_sequence)
        ),

        "lowest_rr": roundit(
            min(rr_sequence)
        ),

        "average_win": roundit(
            average_win
        ),

        "average_loss": roundit(
            average_loss
        ),

        "gross_profit": roundit(
            gross_profit
        ),

        "gross_loss": roundit(
            gross_loss
        ),

        "win_rate": percentage(
            len(wins),
            closed_count,
        ),

        "loss_rate": percentage(
            len(losses),
            closed_count,
        ),

        "breakeven_rate": percentage(
            len(breakevens),
            closed_count,
        ),

        "profit_factor": calculate_profit_factor(
            gross_profit,
            gross_loss,
        ),

        "payoff_ratio": calculate_payoff_ratio(
            average_win,
            average_loss,
        ),

        "median_rr": (
            roundit(calculate_median(rr_sequence))
            if rr_sequence
            else None
        ),

        "expectancy": (
            roundit(expectancy)
            if expectancy is not None
            else 0.0
        ),

        "rr_stddev": calculate_standard_deviation(
            rr_sequence
        ),
    }
