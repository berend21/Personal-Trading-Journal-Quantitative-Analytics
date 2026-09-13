from typing import Iterable

## E = (1/n)SUM_{i=1}^{n} (R_i)
def calculate_expectancy(rr_values: Iterable[float]) -> float | None:

    values = [float(value) for value in rr_values]

    if not values:
        return None

    return sum(values) / len(values)
