# Why the catalog field matters

This repository separates documented Codex behavior from an implementation
detail observed in the open-source Codex client.

## Documented behavior

The current official subagent documentation says:

- local Codex clients support custom agents;
- `gpt-5.6-luna` is suitable for fast, narrow, repeatable agent work;
- `agents.enabled` controls whether multi-agent tools are enabled;
- subagents inherit the parent turn's live permission mode.

Source: [OpenAI subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents).

The official documentation does **not** currently document the model-catalog
`multi_agent_version` field as a user-facing compatibility contract.

## Open-source implementation evidence

Evidence is pinned to OpenAI Codex commit
[`6be2a6ca952ac9f70676ce4dd07fda27175aa9dd`](https://github.com/openai/codex/tree/6be2a6ca952ac9f70676ce4dd07fda27175aa9dd):

1. [`collab_tools_enabled`](https://github.com/openai/codex/blob/6be2a6ca952ac9f70676ce4dd07fda27175aa9dd/codex-rs/core/src/tools/spec_plan.rs#L654-L664)
   permits a v2 root thread, but for a spawned child with an agent path it also
   requires the selected model's `multi_agent_version` to be v2.
2. [The v2 tool registry](https://github.com/openai/codex/blob/6be2a6ca952ac9f70676ce4dd07fda27175aa9dd/codex-rs/core/src/tools/spec_plan.rs#L1232-L1288)
   registers `send_message`, `followup_task`, `wait_agent`, `interrupt_agent`,
   and `list_agents` when collaboration tools are enabled.
3. [`DirectModelOnly`](https://github.com/openai/codex/blob/6be2a6ca952ac9f70676ce4dd07fda27175aa9dd/codex-rs/tools/src/tool_executor.rs#L68-L96)
   means a tool remains directly callable by the model while being excluded
   from the nested Code Mode surface. Therefore a missing entry in a nested
   `ALL_TOOLS` list does not prove that top-level `collaboration.send_message`
   is unavailable.

## Observed failure and success shape

The reproducible failure shape was:

```text
parent turn uses multi-agent v2
+ spawned child has an agent path
+ Luna model-catalog entry is v1
= child does not receive the v2 collaboration tool set
```

The controlled success shape changed only Luna's complete-catalog entry from
v1 to v2, restarted Codex, and generated a fresh child thread. The fresh Luna
child's first tool call was top-level `collaboration.send_message`; the parent
received the internal message before the child's final answer.

## Boundaries

- A custom-agent TOML cannot manufacture a tool that the runtime did not
  register.
- Changing only a session feature flag does not rewrite a model preset.
- A running process or existing thread may keep its already-loaded model
  metadata. Use a full restart and a fresh parent task.
- `send_message_to_thread` is a cross-task API, not internal parent-child
  messaging.
- Permission mode is independent of communication availability. Follow the
  real task's permission needs; do not switch permissions just to test messaging.
- This is an internal implementation detail and may change without notice.
