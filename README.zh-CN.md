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

先调用 `host_session_status`。用 `limit: 200` 调一次 `operation_schema_list`，缓存这份精简目录；只有返回的 revision 变化时才重新读取。接着搜索 operation，只在需要时读取完整参数说明，然后执行：

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

已经知道的一组有序操作应交给 `operation_batch_execute`，不要让每一步都产生一次通信往返。如果 operation 返回 `mode_required`，错误详情会附上 Agent 可直接执行的完整参数数组。由 Supervisor 管理的编辑器会自动重启并校验新模式；普通编辑器在项目权限配置改变后需要重新打开。

## 要求

Infernux `0.3.7` 及以上的 `0.3.x`。
