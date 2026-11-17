"""Explicit selected-case repeat groups, without changing historical campaigns."""
from copy import deepcopy
from dataclasses import asdict

from poisontrace.application.ports import RunGroupStore
from poisontrace.domain import SyntheticCase, investigation_attack
from poisontrace.domain.run_groups import compare_group


class RunGroupService:
    def __init__(self, store: RunGroupStore, runs, profiles):
        self.store, self.runs, self.profiles = store, runs, profiles

    def profile(self, provider):
        runner = self.runs.investigations
        return dict(model=deepcopy(self.profiles[provider]), approved_manifest=[asdict(t) for t in runner.manifest.approved],
                    limits=dict(max_calls=str(runner.max_calls), timeout_seconds=str(runner.timeout_seconds), max_output_bytes=str(runner.max_output_bytes)),
                    scoring_version='investigation-scoring-v1', decision_contract_version='canonical-handling-v2', condition_version='manifest-mcp-v1')

    def create(self, payload):
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
        identifier = self.store.create(plan)
        return self.execute(identifier, {'credential_id':payload['credential_id']} if payload.get('credential_id') else {})

    def execute(self, identifier, payload):
        if set(payload) - {'credential_id'}:
            raise ValueError('reruns use the saved group configuration; only a credential reference may be supplied')
        group = self.store.get(identifier)
        plan = group['plan']
        if plan['execution'] != self.profile(plan['provider']) or (plan['attack'] and plan['attack'] != asdict(investigation_attack(plan['attack']['family']))):
            raise ValueError('runtime or payload changed; create a new group for the new inputs')
        case = SyntheticCase(**plan['case'])
        prepared = {}
        for condition in plan['conditions']:
            request = dict(case_id=case.case_id, mode=condition, provider=plan['provider'], model=plan['model'], **payload)
            if condition != 'clean':
                request['attack_family'] = plan['attack']['family']
            prepared[condition] = self.runs.prepare_investigation(request, case=case)
        slots = [(repeat,condition) for repeat in range(1,plan['repeats']+1) for condition in plan['conditions']]
        attempts = self.store.claim(identifier, slots)
        # Failures returned by the runner are saved results and do not stop the schedule.
        # Process/storage loss leaves explicit unlinked slots; durable recovery is outside this workflow.
        for attempt in attempts:
            selected, configuration, factory = prepared[attempt['condition']]
            configuration = {**configuration, 'group_id':identifier, 'group_attempt':str(attempt['attempt']), 'group_repeat':str(attempt['repeat'])}
            result = self.runs.investigations.run_snapshot(deepcopy(selected), configuration, model_factory=factory)
            self.store.finish_attempt(identifier, attempt['attempt'], result.run_id)
        self.store.finish(identifier)
        return self.get(identifier)

    def get(self, identifier):
        group = self.store.get(identifier)
        results = {}
        for attempt in group['attempts']:
            if attempt['run_id'] is not None:
                try:
                    results[attempt['run_id']] = self.runs.store.result_for(attempt['run_id'])
                except KeyError:
                    pass
        comparison=compare_group(group, results)
        attempts=[]
        for attempt in group['attempts']:
            result=results.get(attempt['run_id'])
            attempts.append({**attempt, 'status':result.status if result else None,
                             'error_category':result.error_category if result else None,
                             'execution_time_ms':result.execution_time_ms if result else None})
        return {**group, 'attempts':attempts, 'comparison':comparison}

    def list(self):
        return [{key:group[key] for key in ('group_id','status','created_at','plan')} for group in self.store.list()]
