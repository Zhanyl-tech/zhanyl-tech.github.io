---
title: "slurm-mcp"
date: 2026-08-23
description: "A read-only MCP server exposing Slurm scheduler state to agents, with the allowlist enforced in code and progressive disclosure of the tool surface."
summary: "A read-only MCP server exposing Slurm scheduler state to agents, with the allowlist enforced in code and progressive disclosure of the tool surface."
tags: [slurm, mcp, agents, hpc, read-only]
status: "Shipped"
repo: "https://github.com/Zhanyl-tech/slurm-mcp"
weight: 7
ShowToc: false
---

**[github.com/Zhanyl-tech/slurm-mcp](https://github.com/Zhanyl-tech/slurm-mcp)** · Python · MIT

A system prompt that says *"only use read-only commands"* is a request, not a
control. It fails open: a jailbreak, a confused tool call, or an ordinary
hallucination is enough to reach `scontrol update` on a production controller.

So the allowlist lives in code and runs on every invocation. `scontrol` is
permitted for `show` and refused for `update`, `reconfigure`, `shutdown` and
eighteen more; shell metacharacters in arguments are refused; commands execute
without a shell. **51 of the tests are real mutating and injection attempts**
rather than assertions about prompt text, because a prompt-level promise cannot
be tested.

**Three tools, not one per binary.** Slurm's flag surface is enormous and mostly
irrelevant to any given question, but a flat design keeps all of it resident in
context. `slurm_overview` answers the question most sessions open with,
`slurm_query` takes a topic from a closed vocabulary, and `slurm_describe`
fetches column meanings for one topic only when they are needed. Measured at
1,088 characters resident against 4,441 for the flat equivalent — and
`make footprint` reproduces that rather than asking anyone to believe it.

That is a context-cost measurement, not a quality claim. Whether it changes an
agent's diagnosis is unmeasured.

Runs against a real cluster or against recorded fixtures with no Slurm
installed.
