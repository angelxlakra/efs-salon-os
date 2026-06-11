"""Proportional discount allocation across bill lines.

GST split billing taxes each line by its own rate and mode, so a bill-level
discount must be pushed down to lines BEFORE tax is computed. Allocation is
proportional to line-total share, floored to the paise; the rounding
remainder is handed out paise-by-paise to the largest lines first (ties broken
by position) so that sum(allocated) == discount exactly and the result is
deterministic.
"""


def allocate_discount(line_totals: list[int], discount: int) -> list[int]:
    """Distribute a bill-level discount across lines proportionally.

    Args:
        line_totals: Per-line totals in paise (zero allowed, e.g. package
            redemption lines — they absorb no discount).
        discount: Total discount in paise.

    Returns:
        Per-line discount amounts, same order as line_totals.

    Raises:
        ValueError: negative inputs, or discount exceeding the lines' sum.
    """
    if discount < 0:
        raise ValueError("Discount cannot be negative")
    if any(lt < 0 for lt in line_totals):
        raise ValueError("Line totals cannot be negative")

    total = sum(line_totals)
    if discount > total:
        raise ValueError(
            f"Discount ({discount}) exceeds sum of line totals ({total})"
        )
    if discount == 0:
        return [0] * len(line_totals)

    # Floor-proportional first pass
    allocated = [(lt * discount) // total for lt in line_totals]

    # Hand the remainder out one paise at a time, largest lines first
    # (position breaks ties), skipping lines already at their cap.
    remainder = discount - sum(allocated)
    order = sorted(range(len(line_totals)), key=lambda i: (-line_totals[i], i))
    while remainder > 0:
        for i in order:
            if remainder == 0:
                break
            if allocated[i] < line_totals[i]:
                allocated[i] += 1
                remainder -= 1

    return allocated
