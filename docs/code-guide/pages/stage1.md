---
id: "stage1"
title: "stage1.py"
group: "Student journey"
order: 105
source: "src/fynd/stages/stage1.py"
summary: "Offers the two Domains and checks whether the student’s Pick was offered."
related: ["stage2", "cli"]
note: "The caller must supply the actual offered list. This file does not save Project or Stage state."
updated: "2026-11-08"
---

## Why this file exists

The Stage owns the Domain rule. Keeping it independent of HTTP and storage means the command line and a future server can call the same logic.

## The flow

1. **Offer**

   Return technology and energy.

2. **Pick**

   Receive a Domain value.

3. **Decide**

   Return DomainKept or DomainNotOffered.

## A small example

```text A Domain Pick
offered = offer_domains()
accept_domain("energy", offered)
# DomainKept(domain="energy")
```

## The pieces inside

| Name               | What it does                                                |
| ------------------ | ----------------------------------------------------------- |
| `SEEDED_DOMAINS`   | The current Domain values: technology and energy.           |
| `DomainKept`       | An accepted Domain value.                                   |
| `DomainNotOffered` | A refused Pick, preserving the value that was sent.         |
| `DomainDecision`   | The union of the two possible outcomes.                     |
| `offer_domains`    | Returns a fresh list, so callers cannot alter the constant. |
| `accept_domain`    | Checks the Pick exactly against the supplied offered list.  |
