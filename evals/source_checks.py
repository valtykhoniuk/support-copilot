"""Shared source attribution checks for golden eval cases."""


def expected_source_needles(case: dict) -> list[str]:
    needles = case.get("expected_sources_any")
    if needles:
        return needles
    single = case.get("expected_sources_contain")
    if single:
        return [single]
    return []


def sources_match(sources: list[str], case: dict) -> bool:
    needles = expected_source_needles(case)
    if not needles:
        return True
    return any(any(needle in source for source in sources) for needle in needles)


def hit_at_k(hits: list[dict], case: dict) -> bool:
    needles = expected_source_needles(case)
    if not needles:
        return False
    return any(any(needle in hit["source"] for hit in hits) for needle in needles)


def reciprocal_rank(hits: list[dict], case: dict) -> float:
    needles = expected_source_needles(case)
    if not needles:
        return 0.0
    best = 0.0
    for needle in needles:
        for i, hit in enumerate(hits, start=1):
            if needle in hit["source"]:
                best = max(best, 1.0 / i)
                break
    return best
