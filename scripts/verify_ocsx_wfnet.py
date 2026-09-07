from __future__ import annotations

from collections import deque
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def local(tag: str) -> str:
    return tag.rsplit('}', 1)[-1]


def parse(path: Path):
    root = ET.parse(path).getroot()
    places = {}
    transitions = set()
    arcs = []
    for elem in root.iter():
        kind = local(elem.tag)
        if kind == 'place':
            pid = elem.attrib['id']
            initial = 0
            for child in elem.iter():
                if local(child.tag) == 'initialMarking':
                    text = next((x.text for x in child.iter() if local(x.tag) == 'text'), None)
                    initial = int(text or '0')
            places[pid] = initial
        elif kind == 'transition':
            transitions.add(elem.attrib['id'])
        elif kind == 'arc':
            arcs.append((elem.attrib['source'], elem.attrib['target']))
    return places, transitions, arcs


def verify(path: Path):
    raw = path.read_text(encoding='utf-8').lower()
    forbidden = ('monitor', 'noprogress', 'no_progress', 't_finish_noprogress')
    found = [term for term in forbidden if term in raw]
    assert not found, f'L1/T2 contamination in L0 WF-net: {found}'

    places, transitions, arcs = parse(path)
    nodes = set(places) | transitions
    outgoing = {n: set() for n in nodes}
    incoming = {n: set() for n in nodes}
    for src, dst in arcs:
        assert src in nodes and dst in nodes, f'unknown arc endpoint: {src}->{dst}'
        outgoing[src].add(dst)
        incoming[dst].add(src)

    initial_places = {p for p, count in places.items() if count == 1}
    assert len(initial_places) == 1, f'exactly one source marking required: {initial_places}'
    assert all(count in (0, 1) for count in places.values()), 'only 1-safe initial markings supported'
    source = next(iter(initial_places))

    sink_places = {p for p in places if not outgoing[p]}
    assert len(sink_places) == 1, f'exactly one sink place required: {sink_places}'
    sink = next(iter(sink_places))
    assert not incoming[source], 'source place must have no incoming arcs'

    def graph_reachable(start, reverse=False):
        edges = incoming if reverse else outgoing
        seen = {start}
        q = deque([start])
        while q:
            n = q.popleft()
            for nxt in edges[n]:
                if nxt not in seen:
                    seen.add(nxt)
                    q.append(nxt)
        return seen

    from_source = graph_reachable(source)
    to_sink = graph_reachable(sink, reverse=True)
    assert nodes <= from_source, f'nodes not reachable from source: {sorted(nodes - from_source)}'
    assert nodes <= to_sink, f'nodes that cannot reach sink: {sorted(nodes - to_sink)}'

    pre = {t: {p for p in places if t in outgoing[p]} for t in transitions}
    post = {t: {p for p in places if p in outgoing[t]} for t in transitions}
    assert all(pre[t] and post[t] for t in transitions), 'each transition needs place pre/post sets'

    start_marking = frozenset({source})
    final_marking = frozenset({sink})
    seen = {start_marking}
    q = deque([start_marking])
    fired = set()
    succ = {}

    while q:
        marking = q.popleft()
        successors = set()
        for t in transitions:
            if pre[t] <= marking:
                new_marking = (set(marking) - pre[t]) | post[t]
                assert len(new_marking) == len(set(new_marking)), 'non-1-safe marking constructed'
                nm = frozenset(new_marking)
                successors.add(nm)
                fired.add(t)
                if nm not in seen:
                    seen.add(nm)
                    q.append(nm)
        succ[marking] = successors

    assert fired == transitions, f'dead transitions: {sorted(transitions - fired)}'
    for marking in seen:
        if sink in marking:
            assert marking == final_marking, f'improper completion marking: {sorted(marking)}'

    reverse_marking = {m: set() for m in seen}
    for m, nexts in succ.items():
        for n in nexts:
            reverse_marking[n].add(m)
    can_finish = {final_marking}
    q = deque([final_marking])
    while q:
        m = q.popleft()
        for prev in reverse_marking[m]:
            if prev not in can_finish:
                can_finish.add(prev)
                q.append(prev)
    assert seen <= can_finish, f'reachable markings without path to completion: {seen - can_finish}'

    print('WFNET_SOUNDNESS=PASS')
    print(f'WFNET_FILE={path.as_posix()}')
    print(f'SOURCE_PLACE={source}')
    print(f'SINK_PLACE={sink}')
    print(f'REACHABLE_MARKINGS={len(seen)}')
    print(f'TRANSITIONS={len(transitions)}')
    print('L0_T2_CONTAMINATION=NONE')


if __name__ == '__main__':
    target = Path(sys.argv[1] if len(sys.argv) > 1 else 'formal/ocsx/ANCESTRAL_WFNET_L0.pnml')
    verify(target)
