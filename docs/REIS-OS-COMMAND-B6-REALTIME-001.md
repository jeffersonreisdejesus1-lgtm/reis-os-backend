# REIS-OS-COMMAND-B6-REALTIME-001

Status: implemented on branch
Base SHA: 6a255a604d790e28211a773957e1419231bf9ed4

## Boundary

B6 adds an authenticated SSE transport over the durable B2 event order. Realtime is transport only; it does not create authority, execute Kernel decisions, fabricate live state, or bypass Command/Kernel boundaries.

## Semantics

- cursor is a zero-based durable event offset;
- reconnect resumes from the supplied cursor;
- batches are capped for backpressure;
- event sequence, source version, freshness, correlation and causation are carried into SSE frames;
- no events => freshness `unknown`, never `live`;
- any stale event => batch freshness `stale`;
- invalid/ahead cursor fails closed;
- `X-Command-Cursor`, `X-Command-Freshness` and connection headers make transport state explicit.

## Tests

Coverage includes durable ordering, reconnect, bounded batches, empty/unknown semantics, stale semantics, ahead-cursor rejection, and SSE causal metadata.

## Non-claims

No delivery claim is promoted from request alone.
No live state is fabricated.
No authority or external effect is introduced.
B7+ is not implemented in this branch.
