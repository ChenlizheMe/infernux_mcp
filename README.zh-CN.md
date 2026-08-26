# Infernux MCP

Infernux MCP 用于把兼容 MCP 的 AI Agent 连接到 Infernux 编辑器。Agent
可以读取项目状态、编辑场景和资产、控制 Play Mode、通过合成输入操作编辑器、
读取语义 UI、捕获引擎渲染目标，并验证独立运行的 Player。

它以 `infernux/mcp` InxPackage 的形式安装，只在编辑器中运行。项目打开时，
插件会为当前项目启动本地 MCP endpoint；项目会话结束时，endpoint 随之关闭。

## 能力

- 查询和编辑场景对象、组件、Transform、材质、Particle Graph、相机及使用
  GUID 标识的资产；
- 进入、暂停、单帧步进、恢复和停止 Play Mode；
- 通过引擎事件链注入键盘、鼠标、滚轮和文本输入；
- 通过 semantic UI snapshot 读取当前帧实际绘制的控件；
- 有界读取编辑器 Console；
- 请求 Scene/Game 渲染目标截图及 GPU object pick；
- 启动、观察、截图、读取日志并正常关闭受管理的 Debug Player；
- 管理验证 attempt、checkpoint、trace 和 blocker report。

## 安装

在 Infernux 插件管理器中安装 `infernux/mcp`，或直接导入发布的 `.inxpkg`
文件。新项目也可以把它列入默认库。它和其它 InxPackage 一样可以禁用、卸载
和重新安装。

默认 endpoint 为 `http://127.0.0.1:9713/mcp`。如需修改监听地址或端口，
请在启动编辑器前设置 `INFERNUX_MCP_HOST` 或 `INFERNUX_MCP_PORT`。

## 调用方式

客户端先搜索 operation schema，再通过 query、command、workflow、batch 或
job gateway 调用选中的稳定 operation ID。

搜索 operation：

```json
{
  "tool": "operation_schema_search",
  "arguments": {"query": "scene object create", "limit": 10}
}
```

执行返回的 command：

```json
{
  "tool": "operation_command_execute",
  "arguments": {
    "operation": "infernux.scene.object.create",
    "arguments": {"name": "AgentCube", "primitive": "cube"}
  }
}
```

已有资产使用 GUID 寻址；场景对象和组件使用查询结果返回的身份标识。修改项目
内容的命令会进入编辑器正常的事务和 Undo 服务。

输入、语义 UI、引擎截图和 Player 验证需要由 Supervisor 管理的 validation
会话。截图只读取引擎渲染目标并写入 review artifact，不使用操作系统或桌面截图。

## 包结构

- `Editor/infernux_mcp`：MCP server 和 operation adapter；
- `InxPluginPages`：插件管理器内的说明页面；
- `InxPackage.json`：`infernux/mcp` 包定义。

本包要求 Infernux `>=0.3.7,<0.4`。
