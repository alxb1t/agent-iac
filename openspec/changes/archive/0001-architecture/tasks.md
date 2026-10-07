# 0001-architecture — tasks

Three phases: the invariants into `CLAUDE.md`, the architecture page, the backlog. Each ends on a green gate.

## Progress

- [x] 1 — Invariants and vocabulary
- [x] 2 — The architecture page
- [x] 3 — The backlog

## 1 — Invariants and vocabulary

- [x] 1.1 Append the `## Invariants (hold for every change)` section from [D10](design.md#d10) to `CLAUDE.md`,
      word for word, after the `## Guardrails` section. Verify: `grep -c '^## Invariants' CLAUDE.md` prints `1`
      and `grep -c 'Creates no machines' CLAUDE.md` prints `1`.
- [x] 1.2 Append the `## Vocabulary — five words, one meaning each` section from [D10](design.md#d10) after it,
      word for word. Verify: `grep -c '^## Vocabulary' CLAUDE.md` prints `1` and `grep -c '\*\*blueprint\*\*' CLAUDE.md` prints `1`.
- [x] 1.3 **HALT CHECK** The template text above the new sections is unchanged.
      Verify: `git diff main -- CLAUDE.md | grep -c '^-[^-]'` prints `0`.

## 2 — The architecture page

- [x] 2.1 Create `docs/architecture.md` with the eight sections named in [the architecture page](design.md#the-architecture-page),
      in that order, each opening with one line on what it decides. Verify: `grep -c '^## ' docs/architecture.md` prints `8`.
- [x] 2.2 Place the box diagram from [D2](design.md#d2) under `## The box`, and the five sentences from [D1](design.md#d1)
      under `## The essence`. Verify: `grep -q 'agent-iac (public collection)' docs/architecture.md && echo ok` prints `ok`.
- [x] 2.3 Place the Hermes manifest block from [D4](design.md#d4) under `## The runtime manifest`, and the `box.yaml`
      block from [D5](design.md#d5) under `## box.yaml`. Verify: `grep -c '^blueprint_mount:' docs/architecture.md` prints `1`
      and `grep -c '^backup:' docs/architecture.md` prints `1`.
- [x] 2.4 Write `## The tiers` as the two-row table from [D8](design.md#d8), and `## Secrets and backups` and
      `## The repos and the knowledge base` from [D6](design.md#d6), [D7](design.md#d7) and [D9](design.md#d9).
      Verify: `grep -c '^| fenced |' docs/architecture.md` prints `1` and `grep -q 'restore drill' docs/architecture.md && echo ok` prints `ok`.
- [x] 2.5 **HALT CHECK** The page names no person, client, vault or machine path.
      Verify: `grep -ci 'marat\|stylist\|katya\|vault\|/Users/' docs/architecture.md` prints `0`.

## 3 — The backlog

- [x] 3.1 Write `.minions/backlog.md`: a `# Backlog` title, a `## 0001-architecture` heading, and one card per
      line of [the cards](design.md#the-cards), in that order, in the shape of [D11](design.md#d11).
      Verify: `grep -c '^- \*\*0001·B' .minions/backlog.md` prints `18` and `grep -c -- '- \*\*Trigger:\*\*' .minions/backlog.md` prints `18`.
- [x] 3.2 **HALT CHECK** The backlog stays untracked, per the line's convention.
      Verify: `git check-ignore -q .minions/backlog.md; echo $?` prints `0`.
