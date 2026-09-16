# Baidu Domain Collector

使用百度公开搜索结果被动收集 `qq.com` 及其子域名的实验代码。项目包含两条独立路线：普通 `requests` 请求，以及复用**已打开的 Edge**页面会话的 `browser-harness` 采集。

## 结论先行

- `requests` 版本保持了接近 Bing 示例的结构，但在本实验中百度首次请求返回了 `302`，并将请求重定向到验证码页面。因此它只记录现象并停止，不会尝试处理或绕过验证。
- `browser-harness` 版本由已有 Edge 发起页面请求、执行页面 JavaScript，并读取已展示的结果 DOM；测试时首页 10 条结果经校验、去重后得到 9 个 `qq.com` 域名。
- 仅运行本仓库的 Python 脚本**不能**自行附着浏览器。使用 browser 版本前，必须单独下载、配置并启动可附着现有 Edge 的 `browser-harness` 工具。

## 目录

```text
baidu-domain-collector/
├── scripts/
│   ├── requests/
│   │   ├── baidu_minimal.py             # 接近 Bing 示例的最小请求版
│   │   └── baidu_requests_detailed.py   # 带跳转、验证与报告记录的详细版
│   └── browser_harness/
│       ├── collect_current_page.py      # 在 Edge 页内执行的 DOM 采集器
│       ├── run_current_page.py          # 读取当前已打开的百度结果页
│       ├── run_search_from_blank_tab.py # 复用当前空白页后自动搜索
│       └── initial_run_current_page.ps1 # 最初的 PowerShell 入口
├── docs/
│   ├── browser-harness.md               # 自写脚本的分层实现思路
│   └── first-test.md                    # 初次 requests/Edge 测试的脱敏记录
├── presentation/
│   └── index.html                       # 可离线打开的实验分享幻灯片
├── tests/
│   └── test_requests_collector.py       # 无网络的 requests 版单元测试
├── requirements.txt
└── LICENSE
```

运行过程写入 `output/`，该目录已被 Git 忽略，避免提交浏览器会话产生的临时结果和跳转参数。

## 分享幻灯片

直接用浏览器打开 [presentation/index.html](presentation/index.html)。幻灯片覆盖 Bing 原脚本、百度 302 验证现象、browser-harness 分层实现、关键代码、域名校验和实验结果；支持按钮、方向键、空格、Home 与 End 翻页。配套的课堂讲稿见 [presentation/speaker-notes.md](presentation/speaker-notes.md)。

## 依赖

普通请求版依赖 Python 3 与 `requests`、`beautifulsoup4`，版本范围见 [requirements.txt](requirements.txt)。请使用已有的 Python 环境准备这些依赖。

浏览器版额外依赖 `browser-harness`。它不随本仓库分发：先从其维护渠道下载/配置该工具，并确保可执行文件在 `PATH` 中；或者在 PowerShell 中指定绝对路径：

```powershell
$env:BROWSER_HARNESS = 'D:\MCP_Servers\browser-harness-conda\Scripts\browser-harness.exe'
```

所有 browser 脚本均复用已打开的 Edge，不新建浏览器、profile 或标签页。它们不读取、复制或保存 Cookie；会话仍由 Edge 按浏览器规则自行使用。

## 使用

### 1. 最小 requests 版

```powershell
& 'D:\Python\python.exe' '.\scripts\requests\baidu_minimal.py'
```

脚本按 `site:qq.com` 请求前三页，读取结果卡片的完整 `mu` 地址，校验域名、去重、排序，并在同目录生成报告。遇到 `302`、`403`、`429`、`503` 或验证码页面时停止并记录。

### 2. 详细 requests 版

```powershell
& 'D:\Python\python.exe' '.\scripts\requests\baidu_requests_detailed.py'
```

该版本额外处理百度 `/link` 的有限跳转和 `meta refresh`，但只请求百度端点；到达外部目标地址时停止，不访问目标网站。

### 3. Edge 当前结果页

先在 Edge 手动打开：

```text
https://www.baidu.com/s?wd=site%3Aqq.com&pn=0&rn=10
```

然后运行：

```powershell
& 'D:\Python\python.exe' '.\scripts\browser_harness\run_current_page.py'
```

### 4. Edge 当前空白页自动开始

Edge 已打开且当前活动页为 `about:blank`、`edge://newtab/` 或默认 Edge 新标签页时：

```powershell
& 'D:\Python\python.exe' '.\scripts\browser_harness\run_search_from_blank_tab.py'
```

该入口只复用活动空白页并导航搜索。活动页不是明确允许的空白页时，返回 `active_tab_not_blank`，不会替换用户正在查看的网页。

## 结果校验

两条路线都只保留符合以下条件的主机名：

1. 是完整的 HTTP/HTTPS URL 中的主机名。
2. 主机名通过 IDNA、长度和 DNS 标签格式检查。
3. 精确等于 `qq.com`，或严格以 `.qq.com` 结尾。

因此 `evilqq.com` 与 `qq.com.example.org` 不会被计入；百度 `/link` 中转域名也不会被当成结果。

## 测试

```powershell
& 'D:\Python\python.exe' -m unittest -v tests.test_requests_collector
```

测试使用伪造 HTML 和 HTTP 响应，不访问百度或 qq.com。

## 观察与限制

完整说明见 [docs/browser-harness.md](docs/browser-harness.md)，初次测试记录见 [docs/first-test.md](docs/first-test.md)，采集器调用与逐段代码解释见 [docs/collect-current-page-walkthrough.md](docs/collect-current-page-walkthrough.md)。搜索结果只反映搜索索引，不能证明域名完整、存活或归属状态。
