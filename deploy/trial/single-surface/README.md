# Single Surface controlled-trial package

Status: implementation package only. Trial execution and production are not
authorized.

This deployment manifest is isolated from the production FastAPI entrypoint.
It uses the Option A topology: a long-running managed/container process plus a
durable relational database. The manifest is not started by repository import
or by the production Docker Compose file.

Builder verification:

```bash
pytest tests/test_single_surface_trial_builder.py
ruff check app/single_surface_trial tests/test_single_surface_trial_builder.py
mypy app/single_surface_trial
```

Mandatory boundaries represented in code/tests:

- one primary active actor per mission;
- monotonic fencing epoch per OCS per mission;
- stale epoch DENY => mutation_count = 0;
- cross-OCS namespace write DENY => mutation_count = 0;
- cross-OCS private-memory import fail-closed;
- source checkpoint required before handoff;
- handoff acceptance receipt required before actor switch;
- listed L2 routes only;
- blind retry forbidden;
- founder-reserved gate cannot be bypassed;
- destructive external effects are never admitted by the trial adapter;
- three-OCS automatic handoff path is builder-verified with synthetic state.

No model provider or external-effect executor is included in this package.
