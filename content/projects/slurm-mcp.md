---
title: "slurm-mcp"
date: 2026-08-23
lastmod: 2026-09-26
description: "A read-only MCP server for Slurm scheduler state: an allowlist of command shapes enforced in code, rate limits for the controller's sake, and three tools with progressive disclosure. Fixture-tested; not yet run against a real cluster."
summary: "A read-only MCP server for Slurm: an allowlist of command shapes enforced in code, and three tools with progressive disclosure. Not yet run against a real cluster."
tags: [slurm, mcp, agents, read-only, python]
status: "v0.2.0 unreleased · fixtures only, no real cluster"
stage: "built"
repo: "https://github.com/Zhanyl-tech/slurm-mcp"
weight: 9
ShowToc: true
---

**[github.com/Zhanyl-tech/slurm-mcp](https://github.com/Zhanyl-tech/slurm-mcp)** · Python · MIT

<p class="project-status"><span class="status status-built">built</span>
The guard, the topic surface and the stdio server are built and tested against
fake Slurm binaries and hand-written fixtures, in-process and over real stdio.
<strong>It has not been run against a real Slurm cluster</strong>, and the
fixtures are illustrative, not recordings.</p>

<!-- OWNER: this page describes the repository's improve/2026-09 branch as of
2026-09-26 (v0.2.0, unreleased). Merge or push it before publishing. -->

A system prompt that says *"only use read-only commands"* is a request, not a
control. It fails open: a jailbreak, a confused tool call, or an ordinary
hallucination is enough to reach `scontrol update` on a production controller.

## The guard is an allowlist of shapes

Version 0.1.0 refused a list of forbidden subcommands, and an audit found
**23** state-changing command lines that passed it: Slurm accepts unique
abbreviations (`scontrol upd` is `update`), an option with a value can hide the
verb, some verbs were missing from the list, and a bare `scontrol` reads
commands from stdin. Version 0.2.0 inverts it. A command must pass two layers:

- **binary shape** — one of seven read binaries, each with only the exact
  option spellings listed for it; `scontrol` only as
  `scontrol show <config|job|node|partition> [name]`; `sdiag` with no options,
  because `sdiag --reset` zeroes the counters a diagnosis reads;
- **topic shape** — exactly one topic's command plus that topic's filters,
  whose values cannot start with `-` or contain whitespace, shell
  metacharacters or control characters.

Commands run without a shell anyway. The tests drive the guard with **70
adversarial command lines** — the 23 bypasses, each with its man-page and
source citation, plus mutations, off-allowlist commands, injections and
off-shape arguments — and every one is refused (counted from the test corpus;
the guard's 104 tests passed on 2026-09-26, and a test keeps the README's
figure equal to the corpus). The stronger
control is Slurm's own authorization: run the server as an unprivileged Slurm
user, and a guard bug that let a write through would still be refused by
`slurmctld`.

A read-only server can still hurt a struggling controller, and squeue's man
page warns against RPC loops, so live reads are cached briefly, capped in
concurrency and rate, and truncated to a row limit with a note saying so. The
defaults are judgement calls, not tuned against a real controller.

## Three tools, not one per binary

`slurm_overview` answers the question most sessions open with, `slurm_query`
takes a topic from a closed vocabulary, and `slurm_describe` fetches column
meanings for one topic only when needed. `make footprint`, run on 2026-09-26:

```
  resident: three tool descriptors    1486 chars
  resident: server instructions        369 chars
  resident total                      1855 chars
  detail, fetched on request          4229 chars
  flat, 7 schemas only                2009 chars  (1.08x resident)
  flat, schemas + inlined detail      6238 chars  (3.36x resident)
```

Read it carefully: a flat server with one schema per binary and no guidance is
about the same size as this one's resident surface. The 3.36× holds only if a
flat server would carry comparable guidance in its descriptions, which is an
assumption, not a measurement. What the measurement does show is that the
4,229 characters of detail stay off the resident path until asked for. (This
page used to quote v0.1.0's 1,088 against 4,441 characters; that ratio rested
mostly on the unstated assumption.)

That is a context-cost measurement, not a quality claim. Whether it changes an
agent's diagnosis is unmeasured.

## Not the only Slurm MCP server

Other public Slurm MCP servers exist, and the ones checked expose write paths
(submit, cancel, hold, requeue). This one differs in scope: read-only by
construction, a closed topic vocabulary instead of a command line, and detail
disclosed on request. A slurmrestd backend, which would suit a server running
next to a Slinky-managed cluster, does not exist yet.
