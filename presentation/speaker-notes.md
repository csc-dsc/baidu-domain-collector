# 《从 Bing 到浏览器会话：域名收集的一次实践》讲稿

建议时长：10 至 12 分钟。以下内容作为讲解备注使用，避免逐字念幻灯片。

## 封面：先说明这是一次工程实验

大家好，今天分享的是一次很小但比较完整的域名收集实验。重点不是“找到了多少域名”，而是从一个简单的 Bing 示例开始，换到百度后遇到验证码，再把失败过程、代码改动和浏览器方案都记录下来。

实验对象是公开搜索结果页，不是直接扫描目标网站。我们只分析搜索引擎已经展示的数据，因此后面看到的域名列表本质上是“被搜索引擎索引到的结果”，不是完整资产清单。

## 01：把需求拆成可验证的输出

域名收集最容易犯的错误是只盯着最终列表。我先把任务拆成三个问题：数据从哪里来，哪些数据可以进入结果，异常时如何说明。

例如，搜索结果里经常出现搜索引擎自己的跳转链接。它看上去是一个 URL，但域名是百度而不是 qq.com。我们必须区分“结果链接”和“结果指向的目标 URL”。另外，零条结果也需要解释：可能真的没有匹配项，也可能是页面结构变化、网络问题或者被验证页拦截。

## 02：Bing 版本的代码结构

这一页的代码最值得学习的是它的结构，而不是 Bing 本身。

requests.get() 把 URL、查询参数、请求头和超时分开写。查询参数以字典传给 params，requests 会自动进行 URL 编码，所以不需要手工拼接 ?q=...。

first = page * 10 + 1 是 Bing 的分页起始序号。Python 的 range(pages) 从 0 开始，所以第一页是 1，第二页是 11，第三页是 21。它和每页的 count = 10 对应。

response.raise_for_status() 的意义是：如果服务器返回 4xx 或 5xx，立即抛出异常，不继续拿错误页去当搜索结果解析。接下来 BeautifulSoup 把 HTML 转成可查询结构，CSS 选择器只拿结果标题链接。

最后使用 set 而不是 list。原因是同一个子域名可能在不同页面、不同 URL 路径中重复出现。集合自动去重，最后 sorted() 让每次结果有稳定顺序，方便对比和写报告。

## 03：百度和 Bing 的真正差别

切换搜索引擎时，不是把 URL 改掉就结束了。百度的关键词参数叫 wd，分页位置叫 pn，每页数量叫 rn。例如 pn=0、10、20 分别对应前三页。

更重要的是链接语义不同。Bing 的标题 href 通常直接指向目标站点；百度标题 href 常是 baidu.com/link?...。如果直接把这个 href 做 urlparse，得到的是百度域名，不能作为 qq.com 的结果。

在测试页面中，百度结果卡片的 mu 属性保存了完整目标 URL。例如卡片标题可以跳转到百度中转页，但 mu 的值已经是 https://mail.qq.com/。因此我们优先解析 mu，而不是把中转地址写入结果。

## 04：为什么要显式处理 302

第一次用 requests 请求百度时，状态码是 302。302 的意思是服务器让客户端到另一个地址继续请求。它不一定代表错误，但本次 Location 指向了百度验证码页面。

这里特意写 allow_redirects=False。默认情况下 requests 会自动跟随重定向，最后我们只能看到验证码页面，反而丢失最初“百度给了 302”和 Location 的证据。关闭自动跳转后，可以同时记录原始状态、跳转位置和后续停止原因。

程序把 403、429、503 和验证页面文字作为停止条件。403 通常表示拒绝访问，429 是明确的频率限制，503 也可能是服务暂时不可用。它们不能在没有服务端日志的情况下被简单归因，但都不应该被当成正常搜索页继续解析。

## 05：从 requests 到 browser-harness 的思路变化

这里不是“让 Python 看起来更像浏览器”，而是让浏览器自己完成网页请求。

普通 requests 维护的是自己的 HTTP 客户端状态。它不会自动读取 Edge 的 Cookie，也不会执行网页里的 JavaScript。即便我们给它换 User-Agent，它的连接特征、Cookie、页面执行环境仍然与浏览器不同。

browser-harness 是一个独立工具。Python 把一段命令交给它，它附着当前已经打开的 Edge，然后在现有页面里运行 DOM 查询。也就是说，网页请求仍然由 Edge 发出，浏览器本身按规则决定使用哪些 Cookie 和页面脚本；我们的 Python 只收到最终提取的 JSON。

这里要特别区分：复用浏览器页面环境，不等于导出或复制 Cookie。脚本没有读取密码、Token、Cookie 数据库或浏览器 profile。

## 06：外层 runner 的逐行说明

外层 runner 的工作其实很单一：读取采集命令、启动 browser-harness、读取标准输出、保存结果。

subprocess.run([HARNESS], ...) 使用的是参数列表而不是拼成一段 shell 字符串。这里的 shell 指 cmd、PowerShell 或 Linux shell 这类命令解释器。若写 shell=True，Python 会先把字符串交给 shell，shell 再按引号、空格、管道符和重定向符解析一次。这里直接传 [HARNESS]，Python 直接启动这个 exe，不经过第二层命令解析，行为更稳定。

HARNESS 的值来自 os.environ.get("BROWSER_HARNESS", "browser-harness")。也就是说，PowerShell 中设置的 BROWSER_HARNESS 会传给 Python；没有设置时，Python 尝试从 PATH 查找名为 browser-harness 的命令。

input=command 表示把内层采集代码从标准输入发送给 browser-harness。注意，command 是 collect_current_page.py 的完整文本，不是它的路径。text=True 和 encoding="utf-8" 是为了保证中文页面标题、日志和 JSON 不会乱码。

process.returncode 是子进程退出状态。约定上 0 表示正常结束，非 0 表示工具发生错误。if process.returncode != 0 这个判断会在工具失败时立刻执行 raise RuntimeError(...)，把 stderr 和 stdout 合并到异常文本中，让外层主程序打印原始错误并以失败状态退出。

capture_output=True 很关键：正常情况下 stdout 应该是 collect_current_page.py 最后 print 出来的 JSON；出错时 stderr 保留 browser-harness 原始错误。return json.loads(process.stdout) 则把 JSON 字符串转成 Python 字典，例如 result["status"]、result["domains"]。如果 stdout 不是合法 JSON，json.loads 会抛出 ValueError，说明不是正常采集结果。timeout=60 则避免工具因为浏览器附着或页面响应异常而无限等待。

保存结果时，JSON 用于证据和追溯，TXT 用于后续简单处理。文件名带时间戳，且使用新建模式，不会覆盖此前实验结果。

## 07：collect_current_page.py 到底如何调用 browser 工具

这一页需要特别说明，collect_current_page.py 不是普通 Python 模块。它最外层是 print(js(r'''...'''))：runner 把整个文件作为标准输入交给 browser-harness；browser-harness 提供 js() 函数；js() 内的立即执行 JavaScript 函数运行在当前 Edge 页中；JSON.stringify(report) 返回给 js()；最外层 print 最终把 JSON 写到 stdout。

所以不要直接执行 python collect_current_page.py，因为系统 Python 没有 js() 函数。它只能通过 run_current_page.py 或 initial_run_current_page.ps1 作为 browser-harness 的命令文本执行。

这里还可以指向 PPT 上的实际调用代码：HARNESS = os.environ.get("BROWSER_HARNESS", "browser-harness") 先读取 PowerShell 中的路径；run_harness(command) 用 subprocess.run([HARNESS], input=command, ...) 启动工具；command 是 collect_current_page.py 的文件内容；工具的 stdout 最后由 json.loads 转成 Python 字典。空白页入口则把 NAVIGATION_PREFIX 和缩进后的采集器拼成同一个 command，再调用同一个 run_harness 函数。

## 08：内层 DOM 采集器如何工作

内层代码运行在网页上下文，所以可以使用 document.querySelectorAll、location.href 等浏览器 API。

先判断当前页是否是百度搜索页，并检查关键词是否正好是 site:qq.com。这一层判断的作用是防止用户切换到别的标签页后，脚本把无关页面当成搜索结果。

对于每个标题链接，anchor.closest(".result, .result-op, .c-container") 的意思是向上寻找最近的结果卡片容器。因为 mu 不一定挂在标题 a 标签上，通常挂在它的父级结果卡片里。

代码把 href、mu、data-landurl、data-log.mu 都放进候选数组，按顺序验证。这样既兼容直接外链，也兼容不同结果模板。只要遇到第一个通过验证的候选 URL，就保存对应的来源字段，便于之后排查页面结构变化。

## 09：域名校验为什么不能只用 contains

如果只判断字符串里有没有 qq.com，就会把 evilqq.com 和 qq.com.example.org 误收集进来。

正确判断是：主机名要么精确等于 qq.com，要么严格以 .qq.com 结尾。前面的点很重要，它确保 mail.qq.com 能通过，但 evilqq.com 不能通过。

代码还检查协议是不是 HTTP 或 HTTPS，拒绝 URL 中的用户名密码部分，处理末尾的点，统一小写，并检查 DNS 标签。比如标签不能以连字符开头，长度不能超过 63。这样的检查不是为了做复杂安全功能，而是为了避免搜索页面中异常或格式损坏的字符串污染结果。

## 10：两个运行入口的取舍

第一个入口只读取当前页面，适合演示和复核。讲解时可以先人工打开百度搜索页，再运行脚本，便于大家看到脚本到底读取了什么。

第二个入口从当前空白标签页开始。它先判断活动页是不是 about:blank、edge://newtab/ 或 Edge 默认新标签页。只有满足条件，才导航到搜索页。

为什么要加这层限制？因为自动化脚本最不应该随意替换用户正在看的网页。如果当前页不是空白页，脚本返回 active_tab_not_blank，相当于把“未执行”也变成一个可解释状态。

## 11：如何读结果

浏览器路径的一次观察中，页面上有 10 条结果卡片，但最终得到 9 个域名。差异不是错误：同一个域名可能对应不同登录入口或不同 URL 路径，集合去重后只保留一次。

结果 JSON 中不仅有域名，还有标题、百度结果链接、目标 URL 和来源属性。TXT 文件只保留域名，适合后续输入其他分析工具。课堂上可以强调，JSON 是证据层，TXT 是使用层，两者用途不同。

这些结果仍然只代表当时百度搜索页展示的内容。它们不是完整子域枚举，也没有证明域名存活或归属。

## 12：方法对比的结论

requests 版本的价值不因为遇到验证就变成零。它清楚展示了最小解析逻辑、百度参数、停止条件和日志记录方式。

browser-harness 版本的价值在于复用了一个正常浏览器页面环境，能直接读取搜索页面已经展示的数据。它不需要把浏览器 Cookie 复制到 Python，也不需要让 Python 模拟所有浏览器行为。

所以这两条路线不是互相替代，而是回答两个不同问题：requests 路线用于理解协议与异常处理；浏览器路线用于读取已正常加载的页面 DOM。

## 13：结束总结

这次实验最重要的收获不是“最后拿到了 9 个域名”，而是把每个环节都做成了可解释的状态。

数据层保证目标 URL 和域边界正确；状态层把 302、429、验证码、空结果节点都记录下来；工程层把最小版本、详细版本、PowerShell 初版、浏览器 Python 入口、离线测试和文档整理成了一个可复现仓库。

如果后续继续完善，我会优先补充页面模板变化时的测试样例和多页结果的稳定解析，而不是把一次观察到的成功结果夸大成通用结论。谢谢大家。
