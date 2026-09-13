"""读取当前已打开的 Edge 百度搜索页。

本脚本调用独立安装的 browser-harness，而不是直接读取浏览器 profile。网页请求、
Cookie 和 JavaScript 都由 Edge 自己处理；本脚本只接收 DOM 采集器输出的 JSON。
"""
import json  # 解析 browser-harness 的 JSON 输出，并保存结构化证据。
import os  # 读取 BROWSER_HARNESS 环境变量并传递 UTF-8 子进程环境。
import subprocess  # 启动本机已安装的 browser-harness 命令行工具。
import sys  # 打印错误并提供标准退出码。
from datetime import datetime  # 生成不会覆盖旧结果的时间戳。
from pathlib import Path  # 用脚本自身位置计算项目根目录。


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output"
# 默认从 PATH 查找 browser-harness；Windows 用户也可设置绝对路径环境变量。
HARNESS = os.environ.get("BROWSER_HARNESS", "browser-harness")


def run_harness(command):
    """将 browser-harness 命令经标准输入发送给当前已打开的 Edge。"""
    process = subprocess.run(
        [HARNESS],  # 不使用 shell，避免命令字符串被再次解释。
        input=command,
        text=True,
        encoding="utf-8",
        capture_output=True,  # stdout 应为 JSON；stderr 保留工具原始错误。
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
        timeout=60,
    )
    if process.returncode != 0:
        raise RuntimeError(process.stderr + process.stdout)
    return json.loads(process.stdout)


def write_results(result, prefix="page"):
    """把一次采集保存为 JSON 证据与逐行域名列表。"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    json_path = OUTPUT_DIR / f"{prefix}-{stamp}.json"
    text_path = OUTPUT_DIR / f"{prefix}-subdomains-{stamp}.txt"
    # x 模式只允许新建文件，时间戳意外重复时不会覆盖旧证据。
    with json_path.open("x", encoding="utf-8") as output:
        json.dump(result, output, ensure_ascii=False, indent=2)
    with text_path.open("x", encoding="utf-8") as output:
        output.write("".join(domain + "\n" for domain in result["domains"]))
    return json_path, text_path


def show_result(result, json_path, text_path):
    """在控制台显示可快速检查的摘要。"""
    print(f"页面状态：{result['status']}；域名数：{len(result['domains'])}")
    for domain in result["domains"]:
        print(domain)
    print(f"证据：{json_path}\n域名：{text_path}")
    if result["status"] != "ok":
        print("未获得正常结果页，已记录状态；未操作验证页面。")


def main():
    # collect_current_page.py 是 browser-harness 的命令文本，不是普通 import 模块。
    command = (SCRIPT_DIR / "collect_current_page.py").read_text(encoding="utf-8")
    result = run_harness(command)
    json_path, text_path = write_results(result)
    show_result(result, json_path, text_path)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"执行失败：{error}", file=sys.stderr)
        sys.exit(1)

