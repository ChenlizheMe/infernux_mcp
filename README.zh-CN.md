# Infernux MCP

让兼容 MCP 的 AI Agent 直接操作 Infernux 编辑器。

装上之后，编辑器进程里会起一个本机服务，默认地址是 `http://127.0.0.1:9713/mcp`。Agent 可以看当前项目、改场景、进 Play Mode，还能把游戏真正渲染出来的画面抓回来。

![Infernux MCP](InxPluginPages/media/system-overview.png)

新项目会默认带着这个包。不需要的话，在「插件」窗口里关掉或卸掉就行。

## 能做什么

- 查、改场景对象、组件、材质、粒子、相机
- 播放、暂停、单帧、停止
- 往游戏里灌键盘和鼠标
- 截 Scene / Game 画面（是引擎画面，不是桌面截图）
- 打出一个独立 Debug Player，并跟它通信

## 怎么连

MCP 客户端指到 `http://127.0.0.1:9713/mcp`。只认本机。换端口的话，启动编辑器前设 `INFERNUX_MCP_PORT`。

## 怎么调

先搜 operation，再读它的参数说明，再执行：

```json
{
  "tool": "operation_schema_search",
  "arguments": {"query": "scene object create", "limit": 10}
}
```

```json
{
  "tool": "operation_command_execute",
  "arguments": {
    "operation": "infernux.scene.object.create",
    "arguments": {"kind": "cube", "name": "AgentCube"}
  }
}
```

别猜字段名。改不熟的组件前先问 `infernux.scene.component.schema`。打 Player 这种慢活用 `operation_job_submit`。

## 要求

Infernux `0.3.7` 及以上的 `0.3.x`。
