# 注意

这是本机开发接口，不是公网服务。只听 localhost。

![仅本机访问](media/trust-gates.png)

每次调用都会核对：有没有这个 operation、参数对不对、项目有没有开这个权限（`ProjectSettings/mcp_capabilities.json`）。改场景走编辑器自己的撤销，不会偷偷改磁盘。

截图来自引擎的 Scene / Game 画面，不会去抓桌面。

关编辑器、认准当前项目、跟 Debug Player 说话，各有一个短期口令。状态接口不会把口令原文吐出来。
