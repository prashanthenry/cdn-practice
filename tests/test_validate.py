"""Unit tests for the validation logic - run with: pytest -q"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from validate import evaluate  # noqa: E402


def test_passes_when_everything_matches():
    check = {"status": 301, "location": "https://www.example.com/"}
    assert evaluate(check, 301, {"Location": "https://www.example.com/"}) == []


def test_wrong_status_is_reported():
    problems = evaluate({"status": 200}, 503, {})
    assert problems == ["status 503, expected 200"]


def test_wrong_redirect_target_is_reported():
    problems = evaluate({"status": 301, "location": "https://www.example.com/"},
                        301, {"Location": "https://example.com/"})
    assert len(problems) == 1 and "Location" in problems[0]


def test_cache_hit_expected():
    assert evaluate({"expect_cache_hit": True}, 200, {"cf-cache-status": "HIT"}) == []
    assert evaluate({"expect_cache_hit": True}, 200, {"cf-cache-status": "MISS"})


def test_not_cached_expected():
    assert evaluate({"expect_not_cached": True}, 200, {"cf-cache-status": "DYNAMIC"}) == []
    assert evaluate({"expect_not_cached": True}, 200, {"cf-cache-status": "HIT"})


def test_header_checks_are_case_insensitive():
    check = {"headers": {"X-Frame-Options": "DENY", "Strict-Transport-Security": "*"}}
    headers = {"x-frame-options": "DENY", "strict-transport-security": "max-age=1"}
    assert evaluate(check, 200, headers) == []


def test_missing_header_is_reported():
    problems = evaluate({"headers": {"X-Frame-Options": "DENY"}}, 200, {})
    assert problems == ["missing header X-Frame-Options"]
