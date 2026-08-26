# 使用

这个包只露出很少几个 MCP 入口。真正能干的事都在 operation 目录里。

![调用 operation](media/agent-loop.png)

1. 搜一下要用的 operation。
2. 把它的参数说明读完，别猜字段名。
3. 按类型调用：查、改，或丢到后台跑。
4. 后面继续用它返回的 ID。资产是 GUID，场景对象以查询结果为准。

改不熟的组件字段前，先问 `infernux.scene.component.schema`。

打 Player 这种慢活用 `operation_job_submit`，再用 `operation_job_status` 看进度，别死等第一次调用。
