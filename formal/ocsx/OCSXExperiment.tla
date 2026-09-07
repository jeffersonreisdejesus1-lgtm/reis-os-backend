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
          executed,
          outcome

vars == <<phase, steps, stopped, stopReason, writer, l0Hash, proposalSeen, executed, outcome>>

Phases == {"OBSERVE", "COGNIZE", "STOP"}
Outcomes == {"UNSET", "Progress", "NoProgress", "Fail"}
StopReasons == {"NONE", "NO_PROGRESS", "FAIL", "BOUND_COMPLETE"}
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
    /\ outcome = "UNSET"

Observe ==
    /\ ~stopped
    /\ phase = "OBSERVE"
    /\ steps < MAX_STEPS
    /\ \E o \in {"Progress", "NoProgress", "Fail"}:
          /\ phase' = "COGNIZE"
          /\ outcome' = o
          /\ proposalSeen' = TRUE
          /\ UNCHANGED <<steps, stopped, stopReason, writer, l0Hash, executed>>

ProgressContinue ==
    /\ ~stopped
    /\ phase = "COGNIZE"
    /\ outcome = "Progress"
    /\ steps < MAX_STEPS
    /\ phase' = "OBSERVE"
    /\ steps' = steps + 1
    /\ outcome' = "UNSET"
    /\ UNCHANGED <<stopped, stopReason, writer, l0Hash, proposalSeen, executed>>

NoProgressUnmonitoredContinue ==
    /\ ~ENABLE_PROGRESS_MONITOR
    /\ ~stopped
    /\ phase = "COGNIZE"
    /\ outcome = "NoProgress"
    /\ steps < MAX_STEPS
    /\ phase' = "OBSERVE"
    /\ steps' = steps + 1
    /\ outcome' = "UNSET"
    /\ UNCHANGED <<stopped, stopReason, writer, l0Hash, proposalSeen, executed>>

NoProgressStop ==
    /\ ENABLE_PROGRESS_MONITOR
    /\ ~stopped
    /\ phase = "COGNIZE"
    /\ outcome = "NoProgress"
    /\ stopped' = TRUE
    /\ stopReason' = "NO_PROGRESS"
    /\ phase' = "STOP"
    /\ outcome' = "NoProgress"
    /\ UNCHANGED <<steps, writer, l0Hash, proposalSeen, executed>>

FailStop ==
    /\ ~stopped
    /\ phase = "COGNIZE"
    /\ outcome = "Fail"
    /\ stopped' = TRUE
    /\ stopReason' = "FAIL"
    /\ phase' = "STOP"
    /\ outcome' = "Fail"
    /\ UNCHANGED <<steps, writer, l0Hash, proposalSeen, executed>>

BoundStop ==
    /\ ~stopped
    /\ phase = "OBSERVE"
    /\ steps >= MAX_STEPS
    /\ stopped' = TRUE
    /\ stopReason' = "BOUND_COMPLETE"
    /\ phase' = "STOP"
    /\ outcome' = "UNSET"
    /\ UNCHANGED <<steps, writer, l0Hash, proposalSeen, executed>>

StoppedStutter ==
    /\ stopped
    /\ UNCHANGED vars

SchedulerStep == Observe \/ ProgressContinue \/ NoProgressUnmonitoredContinue \/ NoProgressStop \/ FailStop \/ BoundStop
Next == SchedulerStep \/ StoppedStutter

Spec == Init /\ [][Next]_vars /\ WF_vars(SchedulerStep)

TypeOK ==
    /\ phase \in Phases
    /\ steps \in Nat
    /\ stopped \in BOOLEAN
    /\ stopReason \in StopReasons
    /\ writer \in Writers
    /\ l0Hash \in STRING
    /\ proposalSeen \in BOOLEAN
    /\ executed \in BOOLEAN
    /\ outcome \in Outcomes

StepBound == steps <= MAX_STEPS
SingleWriter == writer = "SCHEDULER"
L0Immutable == l0Hash = "L0_FROZEN_V1"
AuthorityCeiling == executed = FALSE
NoProposalExecuteBridge == ~(proposalSeen /\ executed)
SingleStop == stopped => (phase = "STOP" /\ stopReason # "NONE")
NoReentryAfterStop == stopped => phase = "STOP"
L0HasNoProgressMonitor == ~ENABLE_PROGRESS_MONITOR => stopReason # "NO_PROGRESS"
NoProgressStopCausality == stopReason = "NO_PROGRESS" => (ENABLE_PROGRESS_MONITOR /\ outcome = "NoProgress")
FailStopCausality == stopReason = "FAIL" => outcome = "Fail"
ProgressNeverMeansNoProgressStop == outcome = "Progress" => stopReason # "NO_PROGRESS"

EventuallyStops == <>stopped
NoProgressWithMonitorEventuallyStops == []((ENABLE_PROGRESS_MONITOR /\ phase = "COGNIZE" /\ outcome = "NoProgress") => <> (stopped /\ stopReason = "NO_PROGRESS"))
StoppedForever == [](stopped => []stopped)
NoReentryTemporal == [](stopped => [](phase = "STOP"))

=============================================================================
