# 使用

这个包只露出很少几个 MCP 入口。真正能干的事都在 operation 目录里。

![调用 operation](media/agent_loop.png)

1. 搜一下要用的 operation。
2. 把它的参数说明读完，别猜字段名。
3. 按类型调用：查、改，或丢到后台跑。
4. 后面继续用它返回的 ID。资产是 GUID，场景对象以查询结果为准。

改不熟的组件字段前，先问 `infernux.scene.component.schema`。

`infernux.scene.open` 和 `infernux.scene.reload` 返回 `scheduled: true` 表示加载已排队。随后查询 `infernux.project.info`：`active_scene.last_load` 包含请求的 `path`、`status`（`pending`、`loading`、`loaded` 或 `failed`）以及具体 `error`。确认该路径已 `loaded` 后再编辑新场景，同时检查 `active_scene.document_state`：若为 `conflict`，表示加载期间磁盘再次变化，已加载的场景并非最新磁盘版本，需要用户处理外部冲突。这两个操作即使用 MCP 后台任务执行，任务完成也只代表排队完成；校验失败时原场景仍保持不变。

`active_scene.document_state` 会显示外部文件冲突状态。保存前通过编辑器的“从磁盘重新加载”“保留本地修改”或“另存为副本”处理冲突。重载与启动使用相同的严格场景格式校验，弹窗会显示解析错误；按错误提示修正文件后再加载。组件 `data` 不应包含 `__type_name__`、`__component_id__` 等运行时元数据。外部编辑器可以使用原子文件替换保存脚本和资产。

打 Player 这种慢活用 `operation_job_submit`，再用 `operation_job_status` 看进度，别死等第一次调用。
