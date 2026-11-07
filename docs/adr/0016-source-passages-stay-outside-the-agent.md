---
status: proposed
date: 2026-11-07
---

# Source passages stay outside the agent

Fynd reads external text that may contain instructions intended to redirect a model. Keep Source text inside extraction calls with no tools, and give any future Stage 3 agent verified Claims, necessary metadata, and structured outcomes rather than Source passages. This trades some context for a smaller exposure to untrusted instructions, while preserving Source passages for student inspection.

This draft records the boundary agreed during the design review. It does not adopt the proposed Stage 3 agent or authorise implementation; ADR 0008 remains the production design.

## The boundary

Extraction prompts wrap and label Source text as data. Extraction calls have no tools they can invoke. Every evidence tool verifies extracted Claims before returning them; the agent cannot choose to skip that verification.

Tool outputs include structured outcomes and counts so the agent can distinguish a failed extraction, no verified Claims, and a missing kind of evidence without reading a Source passage. Explanatory messages are fixed where practical, rather than another model's account of the failure.

A student can inspect a Claim with its surrounding Source passage, Source metadata, original link, and whether the text was an abstract or an Open copy. The passage retrieval function is not an agent tool. Opening evidence in the interface does not add it to the agent's input. The frontend layout is a later decision.

Basic untrusted-data handling applies to extraction and drafting in the fixed workflow too. A small paired injection check of this boundary is baseline work. Apply the agent-specific restriction in the committed post-baseline LangGraph experiment; only production adoption is conditional.

## Limits and trade-off

Verification proves location in Source text, not safety, truth, or relevance. A malicious sentence can survive into a located Claim. Claims and metadata remain untrusted data, never instructions. This boundary reduces exposure and the capabilities available to an attacked extraction call; it does not eliminate prompt injection or replace the proposed injection evaluation.

Giving an agent surrounding passages could help it interpret ambiguous evidence or diagnose a failed search. That context is deliberately withheld. Structured outcomes support search decisions, and students retain access to context for their own judgement. If the restricted interface prevents useful decisions, measure the failure before changing this boundary.

Relying only on a prompt that tells the agent to ignore malicious instructions was rejected as the design approach. The restriction is also in the available tools and the data they return. Making verification an optional agent tool was rejected because it would let the agent omit a product requirement.
