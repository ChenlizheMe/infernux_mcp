# Operation 目录

MCP 表面只发布少量 gateway tools，引擎操作则以正式 OperationSchema 文档的形式位于 gateway 之后。

- 执行前先按领域或能力搜索 schema。
- 只有需要参数契约时才获取完整 schema。
- 已有资产必须通过 GUID 寻址。
- session 或 revision 变化意味着需要重新发现 schema。
- 修改使用 command gateway，只读检查使用 query gateway。

场景、组件、资产、材质、粒子、相机、运行时、checkpoint 和 supervisor operations 都由本插件在 preload 阶段注册。
