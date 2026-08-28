# Minimal fresh-task acceptance prompt

Use this only after the catalog status reports Luna `multi_agent_version=v2`
and Codex has been fully restarted. Replace `<parent-task-name>` with the
canonical parent agent task name returned by the current multi-agent runtime.

```text
Create exactly one gpt-5.6-luna subagent at medium reasoning and standard speed.

Its first action must directly call the top-level collaboration.send_message
tool and send this standalone message to <parent-task-name>:

I am the Luna internal-message probe.
Model: gpt-5.6-luna
Reasoning effort: medium
Speed: standard

After sending, it must immediately return a final answer and enter Done without
waiting for a parent reply. Do not read files, run commands, or change state.

Do not inspect functions.exec ALL_TOOLS. Do not call list_threads or
send_message_to_thread. Those cross-task APIs are not substitutes for internal
parent-child communication. Do not retry or create a second probe.

Pass only if the parent receives an internal MESSAGE before FINAL_ANSWER and the
child reaches Done.
```

Permission profiles and sandbox modes are separate task controls. Do not add a
permission-mode requirement unless the real task or the user explicitly needs
one.
