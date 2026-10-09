# agent-iac — shared context for Claude Code

An Ansible collection, `alxb1t.agent_iac`, whose `box` role makes a host a box; the gate's tools are a `uv` project
beside it.

> **This file is what is true of this repo. It is not a script.** What to do comes from the task you were given.

## The quality gate — `make gate`

The gate is **`make gate`**, run at the repository root. The `Makefile` recipe is the one list of its commands;
prose names `make gate` and never copies them. Today it validates the specs, lints the YAML and the Ansible,
syntax-checks the playbooks and runs the tests. A new command lands through a change whose cut names the gate
recipe in a task. The tests need `sops` and `age` on `PATH`.

## How a change is cut here

Each version is one change, cut, built, checked and released with the MinionsFactory `mf-*` skills. The OpenSpec
CLI is recorded, not pinned: `@fission-ai/openspec@1.11.0`, resolved on `PATH`.

## Layout — where things live here

- **`openspec/`** — the living specs in `specs/`; the changes in `changes/`, the shipped ones in `changes/archive/`.
- **`.minions/`** — run artefacts, **gitignored**; nothing in it is tracked.
- **`CHANGELOG.md`** — Keep a Changelog: each phase appends under `## [Unreleased]`, the release cuts it.

## Guardrails (hold for every role)

- **Never commit a secret, or a real absolute path from the machine the run is on.**
- **Dependencies are minimal and human-approved.** Argue for a new one, and wait for approval before installing it.
- **Never weaken the gate to pass.** A deleted test, a blanket suppression, a loosened config: halt and say so.
- **State lives on disk.** Rebuild where the work is from the active change's `tasks.md` and git.

## Invariants (hold for every change)

- **Generic.** The repo names no person, company or client. Examples use `example`.
- **No plain secret.** A secret is encrypted with sops + age or absent. No token, key or password in clear.
- **Pinned.** Every image, collection and plugin is pinned to a tag or a commit. Nothing follows `latest`.
- **Creates no machines.** agent-iac starts from "a host exists". Flashing a Pi or creating a VPS is outside it.
- **Extends, never wraps.** The agent runs its official image unmodified and never knows agent-iac exists.
- **The box never reaches back.** Nothing on a box names the operator's machine, the vault or this repo's path.
- **One host OS.** Raspberry Pi OS (Debian) today; another host OS lands as a decision, not a branch in a role.

## Vocabulary — five words, one meaning each

**box** · one machine made into a home for one agent — **target** · the machine before it is a box, as SSH
reaches it — **runtime** · one kind of agent, declared by an eight-field manifest — **tier** · what the box
enforces around the agent: `open` or `fenced` — **blueprint** · the agent's own config files, copied in at start.
