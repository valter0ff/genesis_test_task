"""Reliability rubric: confidence assessment from metrics.analyze_topic() output."""

from __future__ import annotations

LEVELS = ["low", "medium", "high"]

MESSAGES: dict[str, dict[str, str]] = {
    "window_short": {
        "en": "The window covers fewer than 24 full months, so year-over-year growth cannot be computed and seasonality is not controlled.",
        "uk": "Вікно охоплює менше 24 повних місяців: річний приріст порахувати не можна, а сезонність не враховано.",
    },
    "no_baseline": {
        "en": "There were no views in the earlier year to compare with.",
        "uk": "У попередньому році переглядів не було, тому порівнювати нема з чим.",
    },
    "very_low_volume": {
        "en": "Fewer than 1,000 views in the last 12 months: too little data for conclusions.",
        "uk": "Менше 1000 переглядів за останні 12 місяців: даних замало для висновків.",
    },
    "low_daily_volume": {
        "en": "Median daily views are below 20, so the numbers are noisy.",
        "uk": "Медіанна кількість переглядів на день менша за 20, тому дані «шумні».",
    },
    "spike_dominated": {
        "en": "More than 30% of views come from short spikes (news, events), not steady interest.",
        "uk": "Понад 30% переглядів припадає на короткі сплески (новини, події), а не на стабільний інтерес.",
    },
    "spike_driven_sign": {
        "en": "The direction of the trend flips when spikes are removed: it is driven by one-off events.",
        "uk": "Напрямок динаміки змінюється, якщо прибрати сплески: її спричинили разові події.",
    },
    "young_article": {
        "en": "The article appeared after the start of the window, so growth partly reflects its creation.",
        "uk": "Стаття з'явилася вже після початку вікна, тому зростання частково пояснюється її створенням.",
    },
    "inconsistent_basket": {
        "en": "Fewer than half of the articles in this topic are growing: the signal is not consistent.",
        "uk": "Менше половини статей теми зростають: сигнал неоднорідний.",
    },
    "platform_trend": {
        "en": "Raw views and views normalized by total Wikipedia traffic move in opposite directions: the platform-wide traffic trend drives the result.",
        "uk": "Сирі перегляди та перегляди, нормалізовані на загальний трафік Вікіпедії, рухаються в різні боки: результат залежить від загального тренду платформи.",
    },
    "all_clear": {
        "en": "No reliability warnings: enough data, no domination by spikes, and the result agrees with raw views.",
        "uk": "Застережень щодо надійності немає: даних достатньо, сплески не домінують, результат узгоджується із сирими переглядами.",
    },
}

LEVEL_LABEL = {
    "en": {"high": "high", "medium": "medium", "low": "low"},
    "uk": {"high": "висока", "medium": "середня", "low": "низька"},
}


def _sign(x: float | None) -> int:
    if x is None or x == 0:
        return 0
    return 1 if x > 0 else -1


def assess(m: dict, lang: str = "en") -> dict:
    """Confidence (high/medium/low) with fired flags and plain-language reasons."""
    lang = lang if lang in MESSAGES["all_clear"] else "en"
    level = 2  # index into LEVELS, start at "high"
    flags: list[str] = []

    def force_low(code: str) -> None:
        nonlocal level
        flags.append(code)
        level = 0

    def downgrade(code: str) -> None:
        nonlocal level
        flags.append(code)
        level = max(0, level - 1)

    if m["months"] < 24:
        force_low("window_short")
    elif m["yoy_norm"] is None:
        force_low("no_baseline")

    if m["volume"]["total_12m"] < 1000:
        force_low("very_low_volume")
    elif m["volume"]["median_daily_12m"] < 20:
        downgrade("low_daily_volume")

    if m["spike_share"] > 0.3:
        downgrade("spike_dominated")

    if _sign(m["yoy_norm"]) != 0 and _sign(m["yoy_ex_spikes"]) != 0 and _sign(m["yoy_norm"]) != _sign(m["yoy_ex_spikes"]):
        force_low("spike_driven_sign")

    if m["young_article"]:
        downgrade("young_article")

    if m["basket_consistency"] is not None and m["basket_consistency"] < 0.5:
        downgrade("inconsistent_basket")

    if _sign(m["yoy_raw"]) != 0 and _sign(m["yoy_norm"]) != 0 and _sign(m["yoy_raw"]) != _sign(m["yoy_norm"]):
        downgrade("platform_trend")

    codes = flags or ["all_clear"]
    return {
        "confidence": LEVELS[level],
        "flags": flags,
        "reasons": [MESSAGES[code][lang] for code in codes],
    }


_DIRECTION_TEMPLATES = {
    "en": {
        "growing": "Interest is growing: {pct:+.0f}% year over year. Reliability: {level}.",
        "declining": "Interest is declining: {pct:+.0f}% year over year. Reliability: {level}.",
        "stable": "Interest is roughly stable: {pct:+.0f}% year over year. Reliability: {level}.",
        "unknown": "Not enough data to estimate the trend. Reliability: {level}.",
    },
    "uk": {
        "growing": "Інтерес зростає: {pct:+.0f}% рік до року. Надійність: {level}.",
        "declining": "Інтерес падає: {pct:+.0f}% рік до року. Надійність: {level}.",
        "stable": "Інтерес приблизно стабільний: {pct:+.0f}% рік до року. Надійність: {level}.",
        "unknown": "Даних замало, щоб оцінити динаміку. Надійність: {level}.",
    },
}


def headline(m: dict, assessment: dict, lang: str = "en") -> str:
    """One-sentence verdict: direction + magnitude + confidence, in `lang`."""
    lang = lang if lang in _DIRECTION_TEMPLATES else "en"
    yoy_norm = m["yoy_norm"]
    if yoy_norm is None:
        key = "unknown"
    elif yoy_norm > 0.10:
        key = "growing"
    elif yoy_norm < -0.10:
        key = "declining"
    else:
        key = "stable"
    level_label = LEVEL_LABEL[lang][assessment["confidence"]]
    return _DIRECTION_TEMPLATES[lang][key].format(pct=(yoy_norm or 0) * 100, level=level_label)
