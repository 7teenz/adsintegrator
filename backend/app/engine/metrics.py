from __future__ import annotations

from statistics import mean


def safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def calc_ctr(clicks: int, impressions: int) -> float:
    return safe_div(clicks * 100, impressions)


def calc_cpc(spend: float, clicks: int) -> float:
    return safe_div(spend, clicks)


def calc_cpm(spend: float, impressions: int) -> float:
    return safe_div(spend * 1000, impressions)


def calc_cpa(spend: float, conversions: int) -> float:
    return safe_div(spend, conversions)


def calc_roas(conversion_value: float, spend: float) -> float:
    return safe_div(conversion_value, spend)


def calc_frequency(impressions: int, reach: int) -> float:
    return safe_div(impressions, reach)


def calc_click_to_conversion_rate(conversions: int, clicks: int) -> float:
    return safe_div(conversions * 100, clicks)


def calc_spend_share(spend: float, total_spend: float) -> float:
    return safe_div(spend, total_spend)


def calc_wow_delta(values: list[float]) -> float:
    if len(values) < 14:
        return 0.0
    current = mean(values[-7:])
    previous = mean(values[-14:-7])
    if previous == 0:
        return 0.0 if current == 0 else 1.0
    return (current - previous) / previous
