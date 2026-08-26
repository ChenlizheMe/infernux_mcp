# Infernux MCP

`infernux/mcp` 是 Infernux 编辑器默认安装、但允许卸载和重装的 MCP Host 插件。它负责 HTTP transport、session/workflow 以及从 OperationSchema 到 MCP 的适配；引擎核心只保留与 transport 无关的 Host registry 和主线程 dispatcher。

默认 MCP 表面只暴露 schema 查询、执行、批处理、workflow、job、capability 和 session gateway。场景与组件编辑、GUID 资产、材质、Particle Graph、编辑器/游戏相机及 Play Mode 等能力作为正式 OperationSchema 由插件直接实现，不存在旧扁平工具或兼容映射。插件全部位于 `Editor/`，因此不会进入 Player 构建。

## 生命周期

`InfernuxMCPPreload` 通过引擎统一的 `InxPreload` AST 扫描发现，不在 manifest 中声明入口。加载时启动 loopback HTTP transport 并注册 `infernux/mcp` 拥有的 operations；卸载时停止接收请求、处理有界任务、关闭 transport、移除对应 operations 与自动生成的客户端发现条目，并释放端口。

新项目依据 `default-libraries.json` 安装该插件。用户主动卸载后，普通启动不会自动装回；需要时可从已验证的官方离线制品重新安装。

## Gateway 模型

默认表面共有 14 个 gateway。客户端应先按领域搜索 operation，再按需获取完整 schema，最后通过相应 gateway 调用稳定的点分 ID。现有资产使用 GUID 寻址；路径只用于上下文或新建目标。场景与组件编辑进入共享 Undo journal，材质编辑使用资源事务，Particle Graph 必须通过严格文档解析和 AOT 编译后才能发布。

切换 profile 仍然是 Supervisor 控制的进程边界。revision 或 session 变化后，客户端必须重新发现 schema。
