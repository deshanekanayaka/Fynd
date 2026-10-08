---
status: accepted
date: 2026-10-08
---

# Technology and Energy ship, and an Invite needs no table

Version 1 holds two Domains. Technology and Energy. Healthcare is cut.

An Invite is one signed code with an expiry date. Fynd stores no `invite` row.

## Why Healthcare lost

Energy holds the Seeded Topic, so Energy stays.

Healthcare has the better official statistics, and that is a real argument for it. It also has the worse Open copy supply, because medical publishing is publisher heavy. The strong full text route for medicine is a biomedical service, and the PRD lists a second live integration as a non-goal.

Healthcare also pulls ethics wording into a student handover, and a bachelor's project that touches patient data needs approval that Fynd cannot speak for.

Technology keeps the Technical core easy to name, and metric 2 grades exactly that.

## Why an Invite needs no storage

A signed code carries its own proof. The server holds the signing secret, reads the code, and accepts or refuses it. A lookup adds nothing to that answer.

What this gives up is the revocation of one leaked code. The only lever left is a rotation of the secret, and that invalidates every code at once. A short expiry keeps the loss small for version 1.

The table arrives the day Fynd needs a use count or a per code revocation. Nothing in version 1 reads either one.

## Consequences

The `project_domain_valid` check constraint lists two values. The Topic prompt names two Domains.

A third Domain is a constraint change, a prompt change, and a new labelled set. The PRD already says that a second Topic waits for metric 1 and metric 2 to pass on the first.

The signing secret lives in the environment. A lost secret means every Invite stops working, and that is the accepted cost.

## Considered options

Healthcare instead of Technology. Rejected for the Open copy supply and the ethics wording. The statistics argument is the one real loss.

All three Domains. Rejected on 2026-10-07, when the measured components entered the plan. See the three week plan in the PRD.

An `invite` table with a use count. Deferred, not rejected. It is a table and two columns on the day a use count matters.
