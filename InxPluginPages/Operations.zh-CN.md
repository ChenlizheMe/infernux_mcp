# Operation 与 Agent 工作流

Infernux MCP 把稳定的 MCP gateway 表面与可发现的引擎 operation 目录分开。
Operation 不只是一个名字；它的 `OperationSchema` 会给出 Agent 安全调用所需的
完整契约。

![Agent operation 工作流](media/agent-loop.png)

## 先发现，再行动

1. 调用 `host_capabilities` 和 `host_session_status`，确认当前项目、模式、
   profile、目录 revision 和已授予的 capability。
2. 使用 `operation_schema_search` 按意图、领域、tag 或 capability 搜索。
3. 使用 `operation_schema_get` 读取完整的参数与返回值契约。
4. 按 schema 声明的 operation kind 选择 gateway 执行。
5. 验证返回状态，并在后续调用中继续使用返回的身份标识。

session 或 operation catalog revision 变化后，应丢弃缓存的参数假设并重新发现
相关 schema。

## Gateway 类型

- **Query**：只读查询状态，不修改项目内容。
- **Command**：通过编辑器事务和 Undo 完成边界明确的修改。
- **Workflow**：协调多阶段引擎任务，并提供结构化进度。
- **Batch**：批量执行兼容的 operation，分别返回每项结果。
- **Job**：异步执行 Player 构建等长任务；客户端使用返回的 job ID 查询进度或
  请求取消。

当客户端已经读取 schema 时，也可以使用通用执行 gateway，由 Host 根据声明的
kind 完成分发。

## 身份与组件契约

资产通过 GUID 而不是项目路径寻址。场景查询会返回后续 operation 所需的对象和
组件身份。修改不熟悉的组件属性前，应调用
`infernux.scene.component.schema`；它是字段类型、枚举值、向量结构、范围和
只读状态的权威定义。

Operation 的结果和错误都面向机器提供结构化信息。Agent 不应仅凭 tool call
成功返回就推断任务完成，而应记录 operation ID、返回的身份、验证证据，以及
任何 blocker。
