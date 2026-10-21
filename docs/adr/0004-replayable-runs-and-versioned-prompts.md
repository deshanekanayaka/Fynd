---
status: accepted
date: 2026-10-07
---

# A run replays from disk, and a prompt is a versioned file

Every prompt lives in its own file under `prompts/`, for example `prompts/propose-topics-v1.md`. No prompt is a string inside a Python file.

Every external call is cached on disk under a key built from five values: the model or API identifier, the hash of the prompt file content, the hash of the input text, the decoding parameters, and the version of the output shape.

The file name carries a version for humans and for the tables, and the key carries the hash of the content. A typo fixed without a rename still misses the cache.

Decoding is fixed. Temperature is zero for all three prompts, which are propose Topics, extract Claims, and draft the Proposal.

### Note added 2026-10-20: the decoding parameter is gone

The Anthropic SDK removed every sampling parameter. `messages.create` in version 1.12.1 does not accept `temperature`, `top_p` or `top_k`, and passing one raises a `TypeError` before a request leaves the machine. The first live stage 2 run found it.

So Fynd sends no decoding parameter, and the cache key names none. The replay promise of this record stands on the cache alone, which is the part that always carried it. An input that was asked once returns the same answer for ever, because the answer is read from disk.

What is lost is the promise across two machines with empty caches. Two first runs of the same prompt can differ, and nothing Fynd can send prevents that. Every published number already carries the model identifier and the prompt hash, so a number stays traceable to what produced it. A number that must be reproducible from nothing now needs the cached answer in git, which is the rule ADR 0011 already states for the Claim set.

Every evaluation result carries the model identifier and the prompt hash that produced it. Nothing in the cache is deleted when a prompt changes.

## Consequences

A whole Project replays from disk with no network and no spend, so the regression tests are repeatable and continuous integration needs no API key.

A prompt edit misses the cache, which is the signal that the old numbers belong to the old prompt. The result rows say which prompt produced which number, so "recall went from 0.86 to 0.91" is traceable to one change.

The Re-roll needs no special case in the key. The round 2 prompt names the ten Topics to avoid, so the input text differs and the key differs on its own. An earlier decision today put the round number in the key, and this entry replaces it.

Temperature zero means two Re-rolls of the same list return the same second list. That is correct for a cache, and a student gets one Re-roll, so nobody meets it.

The cache is the foundation of the evaluation harness and not an optimization. A failed reply is never cached, which an earlier decision already fixed.

## Considered options

A prompt as a string next to the code. Rejected because a prompt change then hides inside a Python diff, and nothing holds a version for the cache key or the result tables.

A version number bumped by hand, with no content hash. Rejected because the day you fix a typo and forget to bump it, every published number silently belongs to a prompt that no longer exists.

A content hash alone, with no human version. Rejected because the tables then read `a3f2c1` where a reader needs `v1`.

Deleting old cache entries when a prompt changes. Rejected because the old answer is the evidence behind the old number.

A temperature above zero for the Topic prompt, for variety. Rejected because a cached call then hides which of several answers you received, and the Re-roll gets its variety from the excluded list instead.
