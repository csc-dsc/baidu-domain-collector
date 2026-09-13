# 由 browser-harness 从 stdin 解释执行；这里的 js() 不是标准 Python 函数。
# 外层脚本把本文件文本发送给 browser-harness，后者在当前 Edge 页中执行 JavaScript。
# 代码仅读取已展示的搜索结果 DOM：不导出 Cookie、不点击结果、不访问 qq.com、不处理验证码。
print(js(r'''(function () {
    // 所有逻辑都封装在立即执行函数中，最后只向外输出一个 JSON 字符串。
    var page = new URL(location.href);
    var report = {
        collected_at: new Date().toISOString(),
        page_url: page.href,
        page_title: document.title,
        status: "",
        records: [],
        domains: []
    };
    // 先检查当前页是否属于百度，防止读取其他标签页中的内容。
    if (page.hostname !== "baidu.com" && !page.hostname.endsWith(".baidu.com")) {
        report.status = "not_baidu";
        return JSON.stringify(report);
    }
    // 将搜索结果标题链接转为普通数组，后续可使用 forEach/map 等数组操作。
    var anchors = Array.from(document.querySelectorAll("#content_left h3 a[href]"));
    var blockText = /百度安全验证|请输入验证码|完成验证|访问过于频繁|访问频率|请求过于频繁|异常请求/;
    if (page.hostname === "wappass.baidu.com" || /captcha|verify|vcode/i.test(page.pathname) ||
        blockText.test(document.title) || (!anchors.length && blockText.test(document.body.innerText))) {
        report.status = "verification_required_stop";  // 有验证提示时只记录，不进行操作。
        return JSON.stringify(report);
    }
    if (!["baidu.com", "www.baidu.com"].includes(page.hostname) ||
        page.pathname !== "/s" || page.searchParams.get("wd") !== "site:qq.com") {
        report.status = "not_target_search_page";
        return JSON.stringify(report);
    }

    function validate(value) {
        // 只接受完整 HTTP(S) URL；浏览器 URL 解析器会规范化主机名。
        if (typeof value !== "string" || /[\s\\\x00-\x1f\x7f]/.test(value)) return null;
        try {
            var url = new URL(value);
            if (!["http:", "https:"].includes(url.protocol) || url.username || url.password) return null;
            var host = url.hostname.toLowerCase().replace(/\.$/, "");
            // 每个 DNS 标签必须由字母、数字、连字符组成，长度不超过 63。
            var labelsOK = host.split(".").every(function (label) {
                return /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(label);
            });
            if (host.length > 253 || !labelsOK) return null;
            if (host !== "qq.com" && !host.endsWith(".qq.com")) return null;
            return {hostname: host, target_url: value};
        } catch (error) { return null; }
    }

    anchors.forEach(function (anchor) {
        // 标题 href 通常是 baidu.com/link；随后尝试百度结果卡片明确声明的完整 URL。
        var candidates = [["href", anchor.href]];
        var card = anchor.closest(".result, .result-op, .c-container");
        [anchor, card].forEach(function (node) {
            if (!node) return;
            ["mu", "data-landurl"].forEach(function (name) {
                candidates.push([name, node.getAttribute(name)]);
            });
            try {
                var log = JSON.parse(node.getAttribute("data-log") || "{}");
                if (log) candidates.push(["data-log.mu", log.mu]);
            } catch (error) { /* 缺失或无效的 JSON 元数据直接跳过。 */ }
        });
        var record = {title: anchor.innerText, result_href: anchor.href};
        // 第一个通过 validate() 的候选项即为本条记录的目标 URL 来源。
        for (var i = 0; i < candidates.length; i++) {
            var result = validate(candidates[i][1]);
            if (result) {
                record.source = candidates[i][0];
                record.target_url = result.target_url;
                record.hostname = result.hostname;
                break;
            }
        }
        if (!record.hostname) record.reason = "没有可确认的目标 URL，跳过百度跳转链接";
        report.records.push(record);  // 每条结果保留来源证据，百度 /link 不作为域名结果。
    });
    // map 取出主机名，filter 去掉无效结果，Set 去重，sort 使输出可重复比对。
    report.domains = Array.from(new Set(report.records.map(function (record) {
        return record.hostname;
    }).filter(Boolean))).sort();  // 集合去重，然后按字母顺序排序。
    report.status = anchors.length ? "ok" : "no_result_nodes";
    report.result_count = anchors.length;
    return JSON.stringify(report);
})()'''))
