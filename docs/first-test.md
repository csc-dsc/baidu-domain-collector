# 初次测试记录

## requests 路线

对 `https://www.baidu.com/s?wd=site%3Aqq.com&pn=0&rn=10` 的首次普通 Python 请求收到了 HTTP `302`，响应位置指向百度验证码页面。请求版按设计记录该状态后停止，没有继续重试、没有处理验证码，也没有访问搜索结果指向的网站。

这说明普通 HTTP 客户端与手工 Edge 浏览的环境不同。仅修改请求头不代表能得到与浏览器相同的风控结果。

## 现有 Edge 路线

使用 browser-harness 附着一个已经打开的 Edge 后，正常显示百度搜索结果页。首页出现 10 条结果，每条结果卡片携带完整的 `mu` 目标地址；经 URL 校验、域名边界过滤、去重和排序后，得到 9 个域名：

```text
a.app.qq.com
aq.qq.com
gongyi.qq.com
id.qq.com
im.qq.com
mail.qq.com
qidian.qq.com
ssl.zc.qq.com
w.mail.qq.com
```

此记录只描述一次实验观察，不保证后续请求一定没有验证码，也不表明存在任何验证码绕过方法。原始响应中的百度跳转参数没有纳入仓库。

