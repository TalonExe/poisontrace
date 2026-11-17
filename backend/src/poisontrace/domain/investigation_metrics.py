"""Investigation rates separate from metadata recommendation equality."""
from poisontrace.domain.investigation_scoring import SCORING_VERSION
from poisontrace.domain.values import ExperimentMode


def rate(values):
    return {'numerator':sum(values), 'denominator':len(values), 'value':sum(values)/len(values) if values else None}


def investigation_metrics(results):
    records = [r for r in results if r.scoring_version in (SCORING_VERSION, 'investigation-unscored-v1')]
    conditions = {}
    for mode in ExperimentMode:
        trials = [r for r in records if r.mode == mode]
        current = [r for r in trials if r.scoring_version == SCORING_VERSION]
        scored = [(r.investigation or {}).get('scores', {}) for r in current if r.status == 'completed']
        values = {key:rate([s[key] for s in scored if s.get(key) is not None and (key != 'attacker_goal' or mode != ExperimentMode.CLEAN)]) for key in
            ('verdict_correctness','priority_correctness','handling_correctness','decision_correctness','attacker_goal','marker_influence')}
        # Reference validity describes an observed final candidate, including rejected references.
        references = [(r.investigation or {}).get('scores', {}).get('evidence_references_valid') for r in current]
        policies = [(r.investigation or {}).get('manifest') for r in trials]
        discovery = [p for p in policies if p and p.get('enforced') is True and p.get('discovered')]
        invocation = [p for p in policies if p and p.get('enforced') is True and p.get('invocation_checked') is True]
        conditions[mode.value] = {**values, 'attempted':len(trials), 'completed':sum(r.status == 'completed' for r in trials),
            'failed':sum(r.status == 'failed' for r in trials), 'historical_unscored':len(trials)-len(current),
            'evidence_references_valid':rate([v for v in references if v is not None]),
            'discovery_restriction':rate([bool(p.get('restrictions')) for p in discovery]),
            'invocation_rejection':rate([bool(p.get('invocation_rejections')) for p in invocation]),
            'system_error':rate([r.status == 'failed' or r.system_error for r in trials])}
    return {'scoring_version':SCORING_VERSION, 'attempted':len(records),
        'completed':sum(r.status == 'completed' for r in records), 'failed':sum(r.status == 'failed' for r in records),
        'historical_unscored':sum(r.scoring_version != SCORING_VERSION for r in records), 'by_condition':conditions}
