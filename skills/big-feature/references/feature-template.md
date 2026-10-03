# FEATURE.md template

Copy this layout to `docs/features/<slug>/FEATURE.md`. Keep the whole file at max 600 words (`feature_max_words`). Remove a section that has no content yet.

```markdown
# <Feature name>

Stage: plan

## Ask

- Feature: <1 line>
- Done when: <numbers, for example "a cast lands a fish in 5 to 20 s of game time at the jetty">
- USER: <the user's words, copied, never changed>
- PROPOSED: <your addition>

## Questions

1. <question>? PROPOSED: <answer>

## Research

Question: <1 fixed question>
- source: research-sources/<file>.md
<short answer>
Words: <n>

## Code check

- Exists: <system> in `scripts/<file>.gd:<line>`
- Missing: <system>

## Options

| | A | B | C |
|---|---|---|---|
| Player sees | ... | ... | ... |
| Files | ... | ... | ... |
| Size | Size: S | Size: M | Size: L |
| Art | Art: 0 (code only) | Art: 2 (asset-forge) | ... |
| Risk | ... | ... | ... |
| Out of scope | Out of scope: ... | Out of scope: ... | Out of scope: ... |

## Tuning numbers

- `data/balance/<system>.json` `<key>`: <value> (editor knob)

## Decision

- Pick: <option> (user, <date>)

## Tickets

1. <job>. Done when: <numbers>. Test (fails first): <test>. test_author: separate agent. coder: <lane>.

No ticket: <item> (<reason>)

## Failed fixes

(feature-breaker writes this section.)
```
