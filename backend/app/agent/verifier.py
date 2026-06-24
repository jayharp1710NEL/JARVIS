"""Verifier — checks how well the draft's claims are grounded in evidence.

Deterministic and honest: it extracts sentence-level claims from the draft and
checks whether their key tokens are supported by the gathered evidence (web
page text, file chunks, math results). It does not pretend a claim is verified
when there is no supporting evidence.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .executor import GatheredContext
from .schemas import Claim

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[a-zA-Z0-9]+")
_STOP = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "be",
    "to", "of", "in", "on", "for", "with", "as", "by", "at", "from", "that",
    "this", "it", "its", "their", "they", "you", "your", "we", "our", "i",
    "can", "will", "may", "also", "which", "these", "those", "such", "than",
    "into", "about", "more", "most", "some", "any", "not", "if", "then",
}
_CITE_RE = re.compile(r"\[(\d+)\]|\[F(\d+)\]")
_HEDGE = ("may", "might", "could", "possibly", "perhaps", "likely", "appears",
          "seems", "reportedly", "estimated", "around", "approximately")


@dataclass
class VerificationReport:
    claims: list[Claim]
    grounded_ratio: float
    unsupported: list[str]
    contradictions: int = 0


def _content_tokens(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if w not in _STOP and len(w) > 2}


def _is_factual_sentence(s: str) -> bool:
    if len(s.split()) < 4:
        return False
    if s.strip().endswith("?"):
        return False
    # skip pure headers / list scaffolding
    if s.strip().startswith(("#", "-", "*", "1.", "2.", "##")):
        return len(s.split()) > 6
    return True


def verify(draft: str, ctx: GatheredContext) -> VerificationReport:
    # Build the evidence token pool, per-source for citation checking.
    source_tokens: dict[str, set[str]] = {}
    for sid, text in ctx.read_texts.items():
        source_tokens[sid.replace("S", "")] = _content_tokens(text)
    for s in ctx.sources:
        idx = s.id.replace("S", "")
        source_tokens.setdefault(idx, set()).update(_content_tokens(s.snippet))
    file_tokens: set[str] = set()
    for ch in ctx.file_chunks:
        file_tokens |= _content_tokens(ch.text)
    global_pool = set().union(*source_tokens.values()) if source_tokens else set()
    global_pool |= file_tokens
    if ctx.math_context:
        global_pool |= _content_tokens(ctx.math_context)

    claims: list[Claim] = []
    unsupported: list[str] = []
    supported = 0
    total = 0

    for sent in _SENT_SPLIT.split(draft):
        sent = sent.strip()
        if not _is_factual_sentence(sent):
            continue
        total += 1
        ctoks = _content_tokens(sent)
        if not ctoks:
            total -= 1
            continue
        cited = _CITE_RE.findall(sent)
        hedged = any(h in sent.lower() for h in _HEDGE)

        status = "uncertain"
        support_ids: list[str] = []

        if cited:
            # check the cited source actually supports the claim tokens
            for web_idx, file_idx in cited:
                if web_idx and web_idx in source_tokens:
                    overlap = ctoks & source_tokens[web_idx]
                    if len(overlap) >= max(2, len(ctoks) // 4):
                        status = "verified"
                        support_ids.append(f"S{web_idx}")
                if file_idx:
                    if ctoks & file_tokens:
                        status = "verified"
                        support_ids.append(f"F{file_idx}")
            if status != "verified":
                status = "likely"  # cited but weak token overlap
        elif global_pool:
            overlap = ctoks & global_pool
            ratio = len(overlap) / max(1, len(ctoks))
            if ratio >= 0.5:
                status = "likely"
            elif ratio >= 0.25:
                status = "uncertain"
            else:
                status = "speculative"
        else:
            status = "speculative" if not hedged else "uncertain"

        if hedged and status == "verified":
            status = "likely"

        if status in ("verified", "likely"):
            supported += 1
        else:
            unsupported.append(sent[:160])

        claims.append(Claim(text=sent[:240], status=status, support=support_ids))

    grounded = supported / total if total else 1.0
    return VerificationReport(
        claims=claims,
        grounded_ratio=round(grounded, 3),
        unsupported=unsupported[:8],
    )
