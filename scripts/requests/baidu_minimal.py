# 本实验通过百度公开搜索结果，被动收集 qq.com 及其子域名。
import sys  # 设置控制台编码。
import re  # 校验域名和识别验证提示。
import time  # 控制请求间隔。
from pathlib import Path  # 保存实验报告。
import requests  # 发送 HTTP 请求。
from bs4 import BeautifulSoup  # 解析搜索结果 HTML。
from urllib.parse import urlparse  # 提取真实 URL 中的主机名。

TARGET_DOMAIN = "qq.com"  # 指定目标域名。
REPORT = Path(__file__).with_name("baidu_minimal_report.txt")  # 独立报告，不覆盖主线。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # 避免中文乱码。


def baidu_search(target_domain=TARGET_DOMAIN, pages=3):
    """提取百度结果中的真实目标域名，校验、去重并排序。"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }  # 保留原版请求头；它不能保证免验证码。
    subdomains = set()  # 集合自动去重。
    logs = [f"实验时间：{time.strftime('%Y-%m-%d %H:%M:%S')}；检索：site:{target_domain}"]
    try:
        for page in range(pages):
            if page:
                time.sleep(3)  # 两页请求之间等待 3 秒。
            response = requests.get(
                "https://www.baidu.com/s",
                params={"wd": f"site:{target_domain}", "pn": page * 10, "rn": 10},
                headers=headers, timeout=15, allow_redirects=False,
            )  # 百度使用 wd、pn、rn；不自动跟随验证码跳转。
            response.encoding = response.apparent_encoding or "utf-8"
            soup = BeautifulSoup(response.text, "html.parser")
            results = soup.select("#content_left .result, #content_left .c-container")
            title = soup.title.get_text() if soup.title else ""
            location = response.headers.get("Location", "")
            logs.append(f"第 {page + 1} 页：HTTP {response.status_code}；标题：{title}；"
                        f"Location：{location}；Retry-After：{response.headers.get('Retry-After', '')}")
            hints = title + location + (soup.get_text() if not results else "")
            if response.status_code in (403, 429, 503) or re.search(
                r"安全验证|请输入验证码|完成验证|访问过于频繁|访问频率|请求过于频繁|wappass\.baidu\.com|captcha", hints
            ):
                logs.append("发现访问限制、服务异常或验证提示，停止请求。")
                break  # 记录现象，不重试或绕过验证。
            if 300 <= response.status_code < 400:
                logs.append("搜索页发生其他跳转，停止并保留 Location 供分析。")
                break
            response.raise_for_status()  # 检查其他 HTTP 错误。
            if not results:
                logs.append("未找到结果节点：可能无匹配项或页面结构变化。")
                break
            for result in results:
                link = result.select_one("h3 a[href]")
                if not link:
                    continue
                real_url = result.get("mu") or link["href"]  # mu 保存完整目标地址，缺失时尝试直接链接。
                try:
                    if re.search(r"[\s\\\x00-\x1f\x7f]", real_url):
                        continue
                    parsed = urlparse(real_url)
                    host = (parsed.hostname or "").encode("idna").decode("ascii").lower().removesuffix(".")
                    _ = parsed.port  # 检查端口格式。
                except (ValueError, UnicodeError):
                    continue
                valid = len(host) <= 253 and all(
                    re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                    for label in host.split(".")
                )  # 检查域名长度、字符和标签两端的横线。
                if (parsed.scheme in ("http", "https") and parsed.username is None
                        and valid and (host == target_domain or host.endswith("." + target_domain))):
                    subdomains.add(host)  # 百度跳转域名和相似的无关域名不会进入结果。
                    logs.append(f"收集：{host}；真实地址：{real_url}")
                else:
                    logs.append(f"跳过：未确认范围内的合法目标地址；链接：{link['href']}")
    except requests.RequestException as error:
        logs.append(f"请求失败，停止：{error}")  # 保留此前已经收集的域名。
    finally:
        logs.append("结果：\n" + "\n".join(sorted(subdomains)))
        logs.append("分析：429 表示限流；403 表示拒绝访问；503 也可能是服务异常。验证可能与请求频率、"
                    "出口 IP、会话环境有关，无法仅凭响应确定原因。无 mu 且不是直接目标链接时跳过；未验证域名存活。")
        REPORT.write_text("\n".join(logs), encoding="utf-8")  # 成功或异常均保存报告。
    return sorted(subdomains)  # 保留 Bing 原版的排序返回方式。


if __name__ == "__main__":  # 直接运行脚本时执行。
    results = baidu_search()
    if results:
        print(f"共发现 {len(results)} 个 {TARGET_DOMAIN} 域名：")
        for domain in results:
            print(domain)
    else:
        print("未取得域名结果，请查看报告；不能据此认定目标没有子域名。")
    print(f"实验报告：{REPORT}")
