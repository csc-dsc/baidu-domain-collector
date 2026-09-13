"""仅复用当前 Edge 空白/新标签页，自动搜索 site:qq.com 后采集结果。"""
import sys  # 输出错误信息并返回非零退出码。
import textwrap  # 将 DOM 采集器缩进到安全导航的 else 分支。

from run_current_page import SCRIPT_DIR, run_harness, show_result, write_results


# 以下文本由 browser-harness 执行。它先判断当前页是否为明确的新标签页，再导航。
NAVIGATION_PREFIX = r"""
is_blank_or_new_tab = js(r'''(function () {
    var current = new URL(location.href);
    return location.href === "about:blank" ||
        location.href === "edge://newtab/" ||
        (current.hostname === "ntp.msn.cn" && current.pathname === "/edge/ntp");
})()''')

if not is_blank_or_new_tab:
    # 不替换用户正在看的页面；只返回一个可保存的状态对象。
    print('{"status":"active_tab_not_blank","domains":[],"records":[],"message":"活动标签页不是允许复用的空白页，未导航。"}')
else:
    # 复用当前空白页，不创建标签页。百度请求仍由 Edge 使用其自身会话发出。
    js('window.location.href = "https://www.baidu.com/s?wd=site%3Aqq.com&pn=0&rn=10"')
    wait(3)  # 等待页面初始加载；验证码和无结果状态由后续 DOM 采集器识别。
"""


def main():
    collector = (SCRIPT_DIR / "collect_current_page.py").read_text(encoding="utf-8")
    # 放入 else 分支可确保非空白页面上不会继续读取或操作 DOM。
    command = NAVIGATION_PREFIX + textwrap.indent(collector, "    ")
    result = run_harness(command)
    json_path, text_path = write_results(result, prefix="auto-page")
    show_result(result, json_path, text_path)
    if result["status"] == "active_tab_not_blank":
        print("活动页面未被替换。请切换到 Edge 空白/新标签页后再运行。")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"执行失败：{error}", file=sys.stderr)
        sys.exit(1)

