import math

from scipy.stats import t

##Ci = X_hat+-t(alpha/2,n-1)*(s/sqrt(n))
#X_hat is sample mean, t is critial value, s is sd, s/sqrt(n) is SE


def confidence_interval(values, confidence=0.95):

    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")

    values = list(values)

    if len(values) < 2:
        return None

    if any(
        
        not isinstance(value, (int, float))
        or not math.isfinite(value)
        for value in values
    ):
        raise ValueError("values must contain only finite numbers")

    n = len(values)

    mean_value = sum(values) / n

    variance = sum(
        (value - mean_value) ** 2
        for value in values
    ) / (n - 1)

    standard_deviation = math.sqrt(variance)
    standard_error = standard_deviation / math.sqrt(n)

    alpha = 1 - confidence

    critical_value = t.ppf(
        1 - alpha / 2,
        df=n - 1,
    )

    margin = critical_value * standard_error

    return {
        "estimate": mean_value,
        "lower": mean_value - margin,
        "upper": mean_value + margin,
        "confidence": confidence,
        "n": n,
        "standard_error": standard_error,
    }
def classify_confidence_interval(result):

    if result is None:
        return "insufficient_data"

    if result["n"] < 10:
        return "insufficient_data"

    if result["lower"] > 0:
        return "positive"

    if result["upper"] < 0:
        return "negative"

    return "inconclusive"



def classify_sample_size(n):

    if n < 10:
        return "very_low"

    if n < 30:
        return "low"

    if n < 100:
        return "moderate"

    return "high"
