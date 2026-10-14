# 注意

这是本机开发接口，不是公网服务。只听 localhost。

![仅本机访问](media/trust_gates.png)

每次调用都会核对 operation、参数和项目权限（`ProjectSettings/mcp_capabilities.json`）。编辑前阅读 schema 的 `reversible` 与 `side_effects`：声明支持撤销的命令走编辑器自己的撤销栈；保存或重载文件、恢复检查点、构建 Player 不能统一通过撤销回滚。

截图来自引擎的 Scene / Game 画面，不会去抓桌面。

关编辑器、认准当前项目、跟 Debug Player 说话，各有一个短期口令。状态接口不会把口令原文吐出来。

HTTP 请求必须携带当前用户的 bearer 凭据。凭据保存在用户状态目录中，不进入项目；IDE 的标准 stdio 代理会自动读取当前凭据，直接连接 HTTP 的客户端需要认证。所有路由都检查 Host，并拒绝带浏览器 Origin 的请求。`/health` 无需凭据，只报告服务是否就绪，不提供项目或所有者信息。

认证后的开发权限属于可信访问，不是沙箱。编写项目 Python 或构建 Player 可以使用编辑器用户的权限执行代码。能力配置用于选择工作流，不隔离代码和该用户。
