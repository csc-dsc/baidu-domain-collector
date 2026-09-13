# browser-harness 版本的实现思路

## 分层

外层 Python 脚本调用本地 `browser-harness` 可执行文件；内层 `collect_current_page.py` 被该工具解释，并在当前 Edge 页面中执行 JavaScript。

```text
Python runner -> browser-harness.exe -> existing Edge -> page DOM -> JSON evidence
```

因此网页请求由 Edge 发出。Edge 自己决定同源 Cookie、会话、页面 JavaScript 和网络连接的处理方式；Python runner 只接收 DOM 采集器输出的 JSON。

## 两个入口

- `run_current_page.py`：当前 Edge 已经停留在 `site:qq.com` 的百度搜索页时使用。它只读取页面，不导航。
- `run_search_from_blank_tab.py`：当前活动页为明确的新标签页/空白页时使用。它复用该页面，导航到百度搜索，然后读取 DOM。非空白页会停止而不会被替换。

## DOM 采集器

采集器依次确认当前页属于百度、包含指定搜索参数、没有验证码或频率限制提示，然后读取 `#content_left h3 a[href]`。

标题 `href` 往往是 `baidu.com/link`。结果卡片的 `mu`、`data-landurl` 和 `data-log.mu` 才是候选的完整目标 URL。候选 URL 必须通过 HTTP(S)、主机名格式和 `qq.com` 域边界检查，最终结果用集合去重并按字母排序。

## 输出

每次成功执行只会在项目根目录的 `output/` 新建两个带时间戳的文件：一个 JSON 证据文件和一个每行一个域名的 TXT 文件。`output/` 已在 `.gitignore` 中，不会被提交到公开仓库。

