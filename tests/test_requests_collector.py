"""请求版的离线测试；所有 HTTP 响应均为本地伪造对象。"""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "requests" / "baidu_minimal.py"
SPEC = importlib.util.spec_from_file_location("baidu_minimal", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def response(body="", status=200, **headers):
    """构造 requests.Response，避免测试向网络发送请求。"""
    result = requests.Response()
    result.status_code = status
    result._content = body.encode("utf-8")
    result.encoding = "utf-8"
    result.headers.update(headers)
    return result


def page(cards):
    return f'<title>百度搜索</title><div id="content_left">{cards}</div>'


def card(url):
    return f'<div class="result c-container" mu="{url}"><h3><a href="/link?url=x">result</a></h3></div>'


class MinimalCollectorTests(unittest.TestCase):
    def test_collects_deduplicated_sorted_valid_domains(self):
        body = page(
            card("https://MAIL.qq.com/") + card("https://mail.qq.com/login") +
            card("https://news.qq.com/") + card("https://evilqq.com/") +
            card("https://qq.com.example.org/") + card("https://-bad.qq.com/")
        )
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.txt"
            with patch.object(MODULE, "REPORT", report), patch.object(
                MODULE.requests, "get", return_value=response(body)
            ) as get, patch.object(MODULE.time, "sleep"):
                domains = MODULE.baidu_search(pages=1)
            self.assertEqual(domains, ["mail.qq.com", "news.qq.com"])
            self.assertTrue(report.exists())
            self.assertFalse(get.call_args.kwargs["allow_redirects"])

    def test_captcha_redirect_stops_without_parsing_results(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.txt"
            with patch.object(MODULE, "REPORT", report), patch.object(
                MODULE.requests, "get", return_value=response(
                    status=302, Location="https://wappass.baidu.com/static/captcha"
                )
            ) as get:
                domains = MODULE.baidu_search(pages=3)
            self.assertEqual(domains, [])
            self.assertEqual(get.call_count, 1)
            self.assertIn("验证提示", report.read_text(encoding="utf-8"))

    def test_http_429_stops_and_writes_observation(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.txt"
            with patch.object(MODULE, "REPORT", report), patch.object(
                MODULE.requests, "get", return_value=response(status=429, **{"Retry-After": "60"})
            ) as get:
                domains = MODULE.baidu_search(pages=3)
            self.assertEqual(domains, [])
            self.assertEqual(get.call_count, 1)
            self.assertIn("HTTP 429", report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

