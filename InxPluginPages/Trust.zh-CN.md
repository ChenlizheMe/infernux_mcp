# 信任门禁

Infernux MCP 使用纵深防御来约束本地 Agent 控制。任何一个 token 都不能单独
取得不受限制的引擎权限，公开状态数据也永远不会包含控制密钥。

![Infernux MCP 信任模型](media/trust-gates.png)

## 第一层：本地传输

MCP Host 只接受 loopback 地址，使 endpoint 保持在本地开发设备内；但
loopback 本身不会被视为充分授权。

## 第二层：Operation 策略

每个请求都必须指向已注册的 operation，并满足它的 `OperationSchema`。Adapter
接触引擎 API 之前，Host 会校验 operation kind、JSON 参数结构，以及
`ProjectSettings/mcp_capabilities.json` 所要求的 capability。

修改编辑器状态的 operation 会进入权威的编辑器执行路径，包括主线程协调、
历史记录、Undo，以及 GUID、对象和组件身份系统。

## 特权控制 Token

- **Supervisor Lease** 属于一个由 Supervisor 拥有的编辑器 session，用于证明
  特权正常关闭请求来自当前 session 的拥有者。
- **Project Lock Token** 属于一个编辑器实例及其项目锁，用于绑定进程、项目
  路径、endpoint、session、profile 与编辑器身份。
- **Player Control Token** 属于一次 Debug Player 启动，用于证明受限 Player
  控制通道上的请求来自这次启动。

Player 通道被刻意限制为输入、观察、引擎截图、日志、运动和关闭。每次重新启动
Player 都会得到一个新的 token。

需要比对身份时，状态 operation 只暴露配置标记和简短的 SHA-256 指纹，永远
不会返回凭据本体。Project Lock Token 保存在本地项目锁元数据中，Lease 和
Player Token 留在拥有它们的进程中；Lease 与 Player 控制路径使用恒定时间
比较验证密钥。

## 观察边界

编辑器和 Player 截图只读取引擎渲染目标，并保存为 review artifact。语义 UI
数据来自 Infernux 实际绘制的控件，不会回退到操作系统桌面截图。

影响更高的编辑器输入、语义 UI 观察和编辑器截图只在 Supervisor 管理的
`global_validation` session 中开放。Debug Player capability 可以单独授予
`developer_assist`，使编辑器交互权限与独立游戏验证保持分离。
