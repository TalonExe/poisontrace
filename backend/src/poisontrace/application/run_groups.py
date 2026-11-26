"""Explicit selected-case repeat groups, without changing historical campaigns."""
from copy import deepcopy
from dataclasses import asdict

from poisontrace.application.ports import RunGroupStore
from poisontrace.domain import investigation_attack
from poisontrace.domain.run_groups import compare_group
from poisontrace.application.runs import require_run_analyst
from poisontrace.application.principals import analyst_owner_id


class RunGroupService:
    def __init__(self, store: RunGroupStore, runs, profiles):
        self.store, self.runs, self.profiles = store, runs, profiles

    def authorize(self, identifier):
        owner = analyst_owner_id()
        if owner is None or self.store.owner_for(identifier) != owner:
            raise KeyError('group not found')

    def profile(self, provider):
        runner = self.runs.investigations
        return dict(model=deepcopy(self.profiles[provider]), approved_manifest=[asdict(t) for t in runner.manifest.approved],
                    limits=dict(max_calls=str(runner.max_calls), timeout_seconds=str(runner.timeout_seconds), max_output_bytes=str(runner.max_output_bytes)),
                    scoring_version='investigation-scoring-v1', decision_contract_version='canonical-handling-v2', condition_version='manifest-mcp-v1')

    def prepare_plan(self, payload):
        require_run_analyst()
        allowed = {'case_id','case_version','provider','model','credential_id','attack_family','conditions','repeats'}
        if set(payload) - allowed:
            raise ValueError('unsupported group configuration')
        if payload.get('provider') == 'scripted' and payload.get('model') not in (None, 'scripted-soc-v2'):
            raise ValueError('scripted groups use model scripted-soc-v2')
        conditions, repeats = payload.get('conditions'), payload.get('repeats')
        if not isinstance(conditions,list) or not conditions or any(c not in ('clean','poisoned','defended') for c in conditions) or len(set(conditions)) != len(conditions):
            raise ValueError('select a nonempty ordered schedule of unique conditions')
        if type(repeats) is not int or repeats < 1:
            raise ValueError('repeat count must be a positive integer')
        case = self.runs.investigations.cases.get(payload.get('case_id'))
        if payload.get('case_version') != case.case_version:
            raise ValueError('case changed; reload before creating a group')
        attacked = any(c != 'clean' for c in conditions)
        family = payload.get('attack_family')
        if not attacked and family is not None:
            raise ValueError('clean-only groups require no attack family')
        if attacked:
            investigation_attack(family)
            if family not in case.supported_attack_families:
                raise ValueError('attack family is not allocated to this case')
        # Validate the entire schedule before any credential or persisted group.
        for condition in conditions:
            self.runs.prepare_investigation({**payload,'mode':condition, 'attack_family':family if condition!='clean' else None}, case=case)
        attack = asdict(investigation_attack(family)) if attacked else None
        provider = payload['provider']
        plan = dict(version='matched-group-v1', case=asdict(case), attack=attack, provider=provider,
                    model=payload.get('model') if provider!='scripted' else 'scripted-soc-v2',
                    conditions=conditions, repeats=repeats, execution=self.profile(provider))
        return plan

    def create(self, payload):
        require_run_analyst()
        raise ValueError('submit groups through durable jobs')

    def execute(self, identifier, payload):
        self.authorize(identifier)
        # Failures returned by the runner are saved results and do not stop the schedule.
        # Process/storage loss leaves explicit unlinked slots; durable recovery is outside this workflow.
        raise ValueError('submit group reruns through durable jobs')

    def get(self, identifier):
        self.authorize(identifier)
        group = self.store.get(identifier)
        results = {}
        for attempt in group['attempts']:
            if attempt['run_id'] is not None:
                try:
                    results[attempt['run_id']] = self.runs.result_for(attempt['run_id'])
                except KeyError:
                    pass
        # A corrupt/legacy association must not disclose a foreign child identifier.
        group['attempts'] = [{**a, 'run_id': a['run_id'] if a['run_id'] in results else None} for a in group['attempts']]
        comparison=compare_group(group, results)
        attempts=[]
        for attempt in group['attempts']:
            result=results.get(attempt['run_id'])
            attempts.append({**attempt, 'status':result.status if result else attempt.get('execution_status') or 'missing',
                             'error_category':result.error_category if result else ('provider_outcome_uncertain' if attempt.get('execution_status') == 'interrupted' else None),
                             'execution_time_ms':result.execution_time_ms if result else None})
        progress = {key: sum(a['status'] == key for a in attempts) for key in ('completed', 'failed', 'interrupted', 'missing', 'queued', 'active')}
        return {**group, 'attempts':attempts, 'comparison':comparison, 'progress':progress}

    def list(self):
        owner = analyst_owner_id()
        groups = (self.store.get(i) for i in self.store.ids_for(owner)) if owner is not None else []
        return [{key:group[key] for key in ('group_id','status','created_at','plan')} for group in groups]
