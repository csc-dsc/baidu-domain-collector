# 本实验通过百度的公开搜索结果，被动收集 qq.com 及其子域名。
import sys  # 设置控制台输出编码。
import re  # 检查域名格式，并识别页面提示。
import time  # 控制请求间隔，记录实验时间。
from pathlib import Path  # 将实验过程保存到报告文件。
from urllib.parse import urlparse, urljoin, urlencode  # 解析、补全和构造 URL。
import requests  # 向百度发送 HTTP 请求。
from bs4 import BeautifulSoup  # 解析百度返回的 HTML。

TARGET_DOMAIN = "qq.com"  # 指定收集范围。
REPORT = Path(__file__).with_name("baidu_simple_report.txt")  # 报告保存在脚本旁。
LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"  # 域名标签最长 63 字符，两端不能是横线。

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # 避免控制台输出中文乱码。


def hostname(url):
    """提取并校验主机名；不符合要求时返回空字符串。"""
    try:
        if re.search(r"[\s\\\x00-\x1f\x7f]", url):
            return ""  # 排除空白、反斜线和控制字符。
        parts = urlparse(url)
        if parts.scheme not in ("http", "https") or parts.username is not None or parts.password is not None:
            return ""  # 只接受 HTTP(S) 地址，排除带用户凭据的地址。
        _ = parts.port  # 检查端口是否是合法数字、是否超出范围。
        host = (parts.hostname or "").encode("idna").decode("ascii").lower().removesuffix(".")
        if len(host) <= 253 and all(re.fullmatch(LABEL, item) for item in host.split(".")):
            return host  # 统一大小写、国际化域名和末尾的点，再检查每个标签。
    except (ValueError, UnicodeError):
        pass  # URL 或域名格式错误时跳过，不让程序崩溃。
    return ""


def read_baidu(session, url, logs):
    """读取百度页面或解析跳转；遇到目标站点地址就返回，不访问目标站点。"""
    for step in range(6):  # 最多请求 5 次，防止跳转循环。
        host = hostname(url)
        parts = urlparse(url)
        if host.endswith(".baidu.com") and (
            host == "wappass.baidu.com" or re.search(r"captcha|verify|vcode", parts.path, re.I)
        ):
            raise RuntimeError("跳转到百度安全验证页面，停止请求。")
        if host not in ("baidu.com", "www.baidu.com") or parts.path not in ("/s", "/link"):
            return url, None  # 已拿到跳转目标，直接交给主程序提取域名。
        if step == 5 or parts.port not in (None, 80, 443):
            logs.append("跳过：跳转次数过多或使用了非常规端口。")
            return "", None
        url = parts._replace(scheme="https", netloc=host).geturl()  # 百度请求统一使用 HTTPS。
        time.sleep(3)  # 每次请求前等待 3 秒；这不能保证不会遇到限流。
        with session.get(url, timeout=15, allow_redirects=False) as response:
            response.encoding = response.apparent_encoding or "utf-8"  # 正确解码中文。
            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.title.get_text(strip=True) if soup.title else ""
            location = response.headers.get("Location", "")
            logs.append(f"请求：{url}\nHTTP：{response.status_code}；标题：{title}\n"
                        f"Location：{location}；Retry-After：{response.headers.get('Retry-After', '')}")
            if response.status_code in (403, 429, 503):
                raise RuntimeError(f"HTTP {response.status_code}：访问受限或服务异常，停止请求。")
            words = r"百度安全验证|请输入验证码|完成验证|访问过于频繁|访问频率|请求过于频繁|异常请求"
            has_results = soup.select_one("#content_left h3 a[href]")
            if re.search(words, title) or (not has_results and re.search(words, soup.get_text())):
                raise RuntimeError("发现验证码或访问频率提示，停止请求。")
            # 检查标题和无结果页面，避免把正常搜索摘要里的“验证码”误判成验证页面。
            response.raise_for_status()  # 将其他 HTTP 错误交给主程序记录。
            if response.status_code in (301, 302, 303, 307, 308) and location:
                url = urljoin(url, location)  # 解析 Location，但不自动访问目标站点。
                continue
            refresh = soup.find("meta", attrs={"http-equiv": re.compile("^refresh$", re.I)})
            match = re.search(r"url\s*=\s*(.+)", refresh.get("content", ""), re.I) if refresh else None
            if match:
                url = urljoin(url, match.group(1).strip().strip("\"'"))
                logs.append(f"HTML 跳转：{url}")  # 兼容 meta refresh，不执行 JavaScript。
                continue
            return url, soup  # 普通搜索页面交给主程序解析。


def baidu_search(pages=3):
    """搜索指定页数，返回校验、去重和排序后的域名列表。"""
    domains = set()  # 集合自动去重。
    logs = [f"实验时间：{time.strftime('%Y-%m-%d %H:%M:%S')}", f"检索条件：site:{TARGET_DOMAIN}"]
    try:
        with requests.Session() as session:  # 同一次实验复用连接和会话。
            session.headers.update({
                "User-Agent": "PassiveDomainLab/1.0",  # 标识实验客户端，不用于绕过安全验证。
                "Accept-Language": "zh-CN,zh;q=0.9",  # 请求优先使用中文页面。
            })
            for page in range(pages):
                url = "https://www.baidu.com/s?" + urlencode({
                    "wd": f"site:{TARGET_DOMAIN}", "pn": page * 10, "rn": 10,
                })  # 百度用 wd 表示关键词，pn=0、10、20 分别表示前三页。
                page_url, soup = read_baidu(session, url, logs)
                links = soup.select("#content_left h3 a[href]") if soup else []
                if not links:
                    logs.append("未找到搜索结果节点：可能无匹配项、需要 JS 或页面结构变化。")
                    break  # 没有可解析结果时停止，不反复请求。
                for link in links:
                    href = urljoin(page_url, link["href"])  # 将相对地址补全为完整 URL。
                    real_url, _ = read_baidu(session, href, logs)  # 解析百度跳转后的真实地址。
                    host = hostname(real_url)
                    if host == TARGET_DOMAIN or host.endswith("." + TARGET_DOMAIN):
                        domains.add(host)  # 排除 evilqq.com 和 qq.com.example.org 等无关域名。
                        logs.append(f"收集：{host}；结果链接：{href}；目标地址：{real_url}")
                    else:
                        logs.append(f"跳过：未解析出范围内的合法域名；结果链接：{href}")
            else:
                logs.append("已完成计划页数。")
    except (requests.RequestException, RuntimeError, ValueError) as error:
        logs.append(f"停止原因：{error}")  # 保留已收集结果，不重试或绕过验证码。
    finally:
        logs.append("结果（去重并排序）：\n" + "\n".join(sorted(domains)))
        logs.append("分析：429 表示限流；403 表示拒绝访问；503 也可能是服务暂时不可用。"
                    "验证码可能与请求模式、出口 IP、会话状态或百度风控策略有关，具体原因无法仅凭响应确定。")
        logs.append("说明：未执行验证或跳转脚本；无法静态解析的链接会跳过。"
                    "结果仅来自搜索索引，未进行 DNS 或存活验证；零结果不代表没有子域名。")
        REPORT.write_text("\n\n".join(logs), encoding="utf-8")  # 成功或异常结束均保存实验报告。
    return sorted(domains)  # 按字母顺序返回去重结果。


if __name__ == "__main__":  # 只有直接运行该文件时才执行下面的代码。
    results = baidu_search(pages=3)  # 默认查询前三页；遇到验证或限流会提前停止。
    print(f"共收集 {len(results)} 个域名：")
    for domain in results:
        print(domain)  # 每行输出一个域名。
    print(f"实验报告：{REPORT}")
