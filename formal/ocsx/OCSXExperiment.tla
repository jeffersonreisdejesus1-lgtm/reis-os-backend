---- MODULE OCSXExperiment ----
EXTENDS Naturals

CONSTANTS ENABLE_PROGRESS_MONITOR, MAX_STEPS

VARIABLES phase,
          steps,
          stopped,
          stopReason,
          writer,
          l0Hash,
          proposalSeen,
          executed

vars == <<phase, steps, stopped, stopReason, writer, l0Hash, proposalSeen, executed>>

Phases == {"OBSERVE", "COGNIZE", "STOP"}
StopReasons == {"NONE", "NO_PROGRESS"}
Writers == {"SCHEDULER"}

Init ==
    /\ phase = "OBSERVE"
    /\ steps = 0
    /\ stopped = FALSE
    /\ stopReason = "NONE"
    /\ writer = "SCHEDULER"
    /\ l0Hash = "L0_FROZEN_V1"
    /\ proposalSeen = FALSE
    /\ executed = FALSE

Observe ==
    /\ ~stopped
    /\ phase = "OBSERVE"
    /\ steps < MAX_STEPS
    /\ phase' = "COGNIZE"
    /\ steps' = steps + 1
    /\ proposalSeen' = TRUE
    /\ UNCHANGED <<stopped, stopReason, writer, l0Hash, executed>>

Cognize ==
    /\ ~stopped
    /\ phase = "COGNIZE"
    /\ steps < MAX_STEPS
    /\ phase' = "OBSERVE"
    /\ UNCHANGED <<steps, stopped, stopReason, writer, l0Hash, proposalSeen, executed>>

NoProgressStop ==
    /\ ENABLE_PROGRESS_MONITOR
    /\ ~stopped
    /\ steps >= MAX_STEPS
    /\ stopped' = TRUE
    /\ stopReason' = "NO_PROGRESS"
    /\ phase' = "STOP"
    /\ UNCHANGED <<steps, writer, l0Hash, proposalSeen, executed>>

L0BoundStutter ==
    /\ ~ENABLE_PROGRESS_MONITOR
    /\ ~stopped
    /\ steps >= MAX_STEPS
    /\ UNCHANGED vars

StoppedStutter ==
    /\ stopped
    /\ UNCHANGED vars

Next == Observe \/ Cognize \/ NoProgressStop \/ L0BoundStutter \/ StoppedStutter

Spec == Init /\ [][Next]_vars

TypeOK ==
    /\ phase \in Phases
    /\ steps \in Nat
    /\ stopped \in BOOLEAN
    /\ stopReason \in StopReasons
    /\ writer \in Writers
    /\ l0Hash \in STRING
    /\ proposalSeen \in BOOLEAN
    /\ executed \in BOOLEAN

StepBound == steps <= MAX_STEPS
SingleWriter == writer = "SCHEDULER"
L0Immutable == l0Hash = "L0_FROZEN_V1"
AuthorityCeiling == executed = FALSE
NoProposalExecuteBridge == ~(proposalSeen /\ executed)
SingleStop == stopped => (phase = "STOP" /\ stopReason # "NONE")
L0HasNoProgressMonitor == ~ENABLE_PROGRESS_MONITOR => stopReason # "NO_PROGRESS"

=============================================================================
