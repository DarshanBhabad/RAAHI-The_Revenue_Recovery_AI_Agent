"""
Redis-backed cache for LLM diagnostic reasoning. Since RAAHI's failure
categories are finite (~10-12 unique root-cause/record-type combinations),
we cache the LLM's narrative+confidence per category instead of calling
the LLM fresh for every single record — dramatically cutting API calls
on large batches without losing reasoning quality.
"""
import json
from upstash_redis import Redis
from app.config import settings

_redis = None
_fallback_cache = {}  # in-memory fallback if Redis isn't configured

CACHE_TTL_SECONDS = 60 * 60 * 24 * 7  # 1 week


def _get_client():
    global _redis
    if _redis is None and settings.upstash_redis_rest_url:
        _redis = Redis(url=settings.upstash_redis_rest_url, token=settings.upstash_redis_rest_token)
    return _redis


def get_cached_diagnosis(record_type: str, failure_reason_code: str) -> dict | None:
    key = f"diag_cache:{record_type}:{failure_reason_code}"
    client = _get_client()

    try:
        if client:
            raw = client.get(key)
            if raw:
                _increment_metric("hits")
                return json.loads(raw)
        else:
            if key in _fallback_cache:
                _increment_metric("hits")
                return _fallback_cache[key]
    except Exception as e:
        print(f"⚠️ Cache read failed ({str(e)[:100]}), treating as miss.", flush=True)

    _increment_metric("misses")
    return None


def set_cached_diagnosis(record_type: str, failure_reason_code: str, narrative: str, confidence: float):
    key = f"diag_cache:{record_type}:{failure_reason_code}"
    value = json.dumps({"narrative": narrative, "confidence": confidence})
    client = _get_client()

    try:
        if client:
            client.set(key, value, ex=CACHE_TTL_SECONDS)
        else:
            _fallback_cache[key] = json.loads(value)
    except Exception as e:
        print(f"⚠️ Cache write failed ({str(e)[:100]}).", flush=True)


def _increment_metric(metric: str):
    client = _get_client()
    try:
        if client:
            client.incr(f"metrics:llm_cache:{metric}")
        else:
            _fallback_cache.setdefault(f"metrics:{metric}", 0)
            _fallback_cache[f"metrics:{metric}"] += 1
    except Exception:
        pass  # metrics are non-critical, never break the pipeline over this


def get_cache_metrics() -> dict:
    client = _get_client()
    try:
        if client:
            hits = int(client.get("metrics:llm_cache:hits") or 0)
            misses = int(client.get("metrics:llm_cache:misses") or 0)
        else:
            hits = _fallback_cache.get("metrics:hits", 0)
            misses = _fallback_cache.get("metrics:misses", 0)
    except Exception:
        hits, misses = 0, 0

    total = hits + misses
    hit_rate = round((hits / total * 100), 2) if total > 0 else 0.0
    calls_saved = hits  # each hit is one LLM call we didn't need to make

    return {
        "cache_hits": hits,
        "cache_misses": misses,
        "total_lookups": total,
        "hit_rate_pct": hit_rate,
        "llm_calls_saved": calls_saved,
    }