from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.execution_bindings import _authorize_caller
from app.trading_runtime.economics import BudgetPolicy, EconomicGovernor


def test_execution_binding_requires_configured_caller_auth(monkeypatch):
    monkeypatch.delenv("REIS_EXECUTION_BINDINGS_CALLER_TOKEN", raising=False)
    with pytest.raises(HTTPException) as exc:
        _authorize_caller(None)
    assert exc.value.status_code == 503


def test_execution_binding_rejects_wrong_caller_token(monkeypatch):
    monkeypatch.setenv("REIS_EXECUTION_BINDINGS_CALLER_TOKEN", "expected-secret")
    with pytest.raises(HTTPException) as exc:
        _authorize_caller("wrong-secret")
    assert exc.value.status_code == 401
    _authorize_caller("expected-secret")


def _policy(strong_limit=1):
    return BudgetPolicy(
        daily=Decimal("10"),
        monthly=Decimal("100"),
        run=Decimal("10"),
        signal=Decimal("1"),
        cycle_call_limit=10,
        strong_model_limit=strong_limit,
    )


def test_strong_quota_counts_outstanding_reservations_atomically():
    governor = EconomicGovernor(_policy(strong_limit=1))
    first = governor.reserve(Decimal("0.1"), strong=True)
    assert first is not None
    assert governor.reserve(Decimal("0.1"), strong=True) is None
    assert governor.strong_calls_today == 0


def test_strong_classification_cannot_be_omitted_at_reconciliation():
    governor = EconomicGovernor(_policy(strong_limit=1))
    reservation = governor.reserve(Decimal("0.1"), strong=True)
    assert reservation is not None
    assert governor.reconcile(reservation.reservation_id, Decimal("0.1")) is False
    assert governor.reserve(Decimal("0.1"), strong=True) is None
    assert governor.reconcile(
        reservation.reservation_id, Decimal("0.1"), strong=True
    )
    assert governor.strong_calls_today == 1
