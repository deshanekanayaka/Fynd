"""Groups the Domain and Topic rules used by Fynd's command-line flow.

stage1 offers and accepts Domains; stage2 proposes and checks Topics.
Callers supply external-service functions and own saving, so the rules can
also be reused by the future runner (ADR 0006).
"""
