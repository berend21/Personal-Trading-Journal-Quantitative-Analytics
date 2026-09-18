from datetime import datetime

def smart_price(value):
    try:
        if value is None:
            return ""
        val = float(value)
        if val == 0:
            return "0"
        abs_val = abs(val)
        if abs_val < 1e-6:
            return f"{val:.2e}"

        if abs_val < 0.01:
            prec = 8
        elif abs_val < 1:
            prec = 6
        elif abs_val < 10:
            prec = 5
        elif abs_val < 1000:
            prec = 3
        elif abs_val < 10000:
            prec = 2
        elif abs_val < 100000:
            prec = 1
        else:
            prec = 0

        formatted = f"{val:.{prec}f}"
        formatted = formatted.rstrip('0').rstrip('.') if '.' in formatted else formatted
        return formatted
    except Exception:
        return str(value)

def parse_time(s):
    if not s:
        return None
    s = s.replace('T', ' ').strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None

