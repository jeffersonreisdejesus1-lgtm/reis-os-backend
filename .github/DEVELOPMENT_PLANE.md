# Development plane — authorized Git mutation

PLANE = DEVELOPMENT
INSTITUTIONAL_CONTROL = SEPARATE

Connected hosts (ChatGPT, Grok, other OCS executors) acting as the repository owner **may**:

- create and update files on non-`main` branches
- create branches
- commit
- open issues
- open draft pull requests
- run tests

They **must not**:

- merge to `main` without Founder authorization
- promote gates
- self-assure
- expand authority
- treat a successful write as institutional adoption

`CODE_MUTATION != INSTITUTIONAL_PROMOTION`

There is no repository-local hook, CODEOWNERS file, or ruleset in this private Free-plan repo that can deny `create_file` or `create_issue`.

If a host still refuses those calls, the blocker is the **host platform security layer**, not REIS OS code. Disable or re-authorize that host's GitHub connector in the host product settings. Do not delete identity or gate code to work around it.
