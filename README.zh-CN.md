# Codex Luna 内部父子消息

[English](README.md)

这是一个小型、可审计的工具，用于检查并安全修改完整 Codex 模型目录中与
`gpt-5.6-luna` 子代理 v2 协作工具相关的字段。

> **重要：** `multi_agent_version` 是 Codex 当前开源实现中的内部细节，不是官方文档承诺的
> 稳定用户配置。修改前必须备份、审查差异，并预期未来 Codex 版本可能改变此机制。

## 它解决什么

在受影响的运行路线中，父代理已经拥有多代理工具，但带 agent path 的 Luna 子线程仍可能没有
内部 `collaboration.send_message`。当前 OpenAI Codex 开源实现要求：v2 子线程除了会话采用
v2 外，所选模型对象自身也必须标记 `multi_agent_version=v2`。

本工具只做以下事情：

- 只读取你显式传入的完整 JSON 模型目录；
- 写入前要求 fresh SHA-256 比较并交换；
- 要求目录中恰好有一个 `gpt-5.6-luna`；
- 只把 Luna 的 `multi_agent_version` 从缺失/v1 改为 v2；
- 自动创建带时间戳的备份；
- 在同一目录原子替换并复核结果；
- 不修改 `config.toml`、不切换权限、不重启 Codex。

实现证据和边界见 [docs/INTERNALS.md](docs/INTERNALS.md)。

## 环境要求

- Python 3.10 或更新版本
- 完整 Codex JSON 模型目录
- 支持多代理 v2 的 Codex 版本

## 先只读检查

在仓库根目录运行：

```powershell
$env:PYTHONPATH = "$PWD\src"
py -3 -X utf8 -m codex_luna_internal_messaging status `
  --catalog "C:\path\to\complete-model-catalog.json"
```

命令只返回目录 SHA-256、模型数量和 Luna 的相关状态，不打印模型提示或其他目录内容。

## Dry-run 与启用

从 fresh `status` 结果复制 SHA-256：

```powershell
$catalogSha = "<fresh status sha256>"

py -3 -X utf8 -m codex_luna_internal_messaging enable `
  --catalog "C:\path\to\complete-model-catalog.json" `
  --expected-sha256 $catalogSha `
  --dry-run
```

审查结果后，移除 `--dry-run` 才会创建备份并应用单一语义修改：

```powershell
py -3 -X utf8 -m codex_luna_internal_messaging enable `
  --catalog "C:\path\to\complete-model-catalog.json" `
  --expected-sha256 $catalogSha
```

写入器会把 JSON 格式规范化为两空格缩进；除 Luna 的 `multi_agent_version` 外，所有模型对象和
字段在语义上保持不变，原始字节保存在返回的备份路径中。

## 让新进程加载并验收

1. 确认 Codex 的 `model_catalog_json` 指向你刚审查的完整目录；本工具不修改该设置。
2. 完整重启 Codex，使进程重新加载模型元数据。
3. 新建父任务；已有任务可能继续保留旧模型对象。
4. 使用[最小验收提示](prompts/verify-internal-message.md)。
5. 只有父代理先收到真实内部 `MESSAGE`、随后收到子代理 `FINAL_ANSWER`，且子线程进入
   `Done`，才算通过。

不要用嵌套 `functions.exec` 的 `ALL_TOOLS` 判断顶层工具不存在。不要用 `list_threads` 或
`send_message_to_thread` 替代内部父子通信。

## 权限是另一条边界

[OpenAI 官方子代理文档](https://learn.chatgpt.com/docs/agent-configuration/subagents)说明子代理继承
父任务当前的权限模式。验证通信不需要切换 Full access 或 Read-only。权限只有在具体任务本身
需要限制，或用户明确要求时，才单独核对。

## 测试

```powershell
py -3 -X utf8 -m unittest discover -s tests -v
```

测试覆盖只读状态、单字段启用、备份、幂等、dry-run、SHA-256 不匹配拒绝、重复 Luna 拒绝和
未知版本拒绝。

## 许可证

MIT。本项目独立维护，不是 OpenAI 官方产品。
