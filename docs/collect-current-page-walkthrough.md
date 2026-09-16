# collect_current_page.py 逐段说明

这个文件容易被误解成“普通 Python 脚本”，实际上不是。

它的执行者是 browser-harness。外层 runner 读取整个文件的文本，并用标准输入交给 browser-harness。browser-harness 的命令解释器提供两个额外函数：

- js(表达式)：在当前 Edge 页面中运行 JavaScript，并返回表达式结果。
- wait(秒数)：等待页面加载。

因此，这个文件不能直接用 python collect_current_page.py 运行。直接运行时 Python 不认识 js()。

## 1. 最外层包装

文件的结构可以简化为：

    print(js(r'''(function () {
        // JavaScript 逻辑
        return JSON.stringify(report);
    })()'''))

最外层 print 是 browser-harness 命令解释器中的 Python 调用。

js 的参数是一段 JavaScript 字符串。字符串里的立即执行函数，也就是 function() { ... }()，会在当前 Edge 标签页的网页上下文运行。它读取 location、document 和搜索结果 DOM。

JavaScript 最后返回 JSON.stringify(report)。browser-harness 把这个字符串作为 js() 的返回值交给 print，因此外层 Python runner 的 process.stdout 是一个 JSON 字符串。

完整调用方向：

    run_current_page.py
      -> 读取 collect_current_page.py
      -> subprocess.run([browser-harness], input=文件文本)
      -> browser-harness 执行 print(js(...))
      -> Edge 当前页执行 JavaScript
      -> stdout 输出 JSON
      -> json.loads(process.stdout)

## 2. 先建立 report，而不是直接打印域名

JavaScript 一开始创建 report：

    var report = {
        collected_at: new Date().toISOString(),
        page_url: page.href,
        page_title: document.title,
        status: "",
        records: [],
        domains: []
    };

records 保存逐条搜索结果及其来源证据。domains 是最终去重后的域名列表。

分开保存的原因是：TXT 文件适合后续使用，JSON 文件适合复核。页面结构变化、结果缺少 mu 属性或某条链接被跳过时，都可以从 records 中定位原因。

## 3. 为什么先检查页面范围

采集器首先检查 host、路径和关键词：

    page.hostname
    page.pathname === "/s"
    page.searchParams.get("wd") === "site:qq.com"

这能防止当前 Edge 被切换到另一个标签页时，脚本误读无关网页。

验证码页面也有单独状态。只要页面属于 wappass.baidu.com、路径包含 captcha、verify 或 vcode，或者标题与正文出现验证提示，函数立即返回：

    status = "verification_required_stop"

返回状态后不继续解析，不点击、不填写验证码，也不请求搜索结果指向的网站。

## 4. 为什么标题 href 不是优先的真实目标

百度标题通常类似：

    https://www.baidu.com/link?url=...

它用于百度统计和跳转，主机名是百度，不是 qq.com。

所以对每条标题链接，代码先找到外层结果卡片：

    var card = anchor.closest(".result, .result-op, .c-container");

然后收集多个可能的完整目标 URL：

    var candidates = [["href", anchor.href]];
    candidates.push(["mu", node.getAttribute("mu")]);
    candidates.push(["data-landurl", node.getAttribute("data-landurl")]);
    candidates.push(["data-log.mu", log.mu]);

候选项按顺序验证。只有 href 本身已经是目标 URL 时才会通过；更常见的是 mu 通过。record.source 会记录最终命中的属性名称。

## 5. validate() 做了哪些检查

validate() 不只是取 hostname，而是逐层拒绝不可信或格式错误的值：

1. 只允许字符串；拒绝空白、反斜线和控制字符。
2. 只接受 HTTP 或 HTTPS URL。
3. 拒绝 URL 用户名和密码部分，例如 https://user@host。
4. 使用浏览器 URL 解析器得到规范化主机名。
5. 检查主机名总长度和每个 DNS 标签的格式。
6. 只允许 qq.com 或严格以 .qq.com 结尾。

最后一条避免字符串包含判断造成的误收集：

    evilqq.com           不属于 qq.com
    qq.com.example.org   不属于 qq.com
    mail.qq.com          属于 qq.com

通过校验后，函数返回 hostname 和原始 target_url。失败返回 null。

## 6. 最后如何去重和排序

每条结果先保存到 records。最终结果由 records 推导：

    report.domains = Array.from(new Set(
        report.records.map(function (record) {
            return record.hostname;
        }).filter(Boolean)
    )).sort();

map 取出每条记录的 hostname，filter(Boolean) 丢弃没有通过校验的空值，Set 去重，sort 使输出稳定。

这样同一个 mail.qq.com 即使在多个不同登录 URL 中出现，最终 TXT 也只保留一行。

## 7. 与外层 runner 的边界

collect_current_page.py 只做“从已显示页面读取并产生 JSON”。

run_current_page.py 只做“调用 browser-harness、处理错误、把 JSON 写成文件”。

这种分层有两个好处：

- 页面解析逻辑可以在 browser-harness 命令环境单独检查。
- 文件输出、时间戳和异常报告不需要混进网页 JavaScript。

相关文件：

- scripts/browser_harness/run_current_page.py：外层 runner。
- scripts/browser_harness/collect_current_page.py：当前 Edge 页内的 DOM 采集器。
- scripts/browser_harness/run_search_from_blank_tab.py：复用当前空白页并导航搜索的入口。
