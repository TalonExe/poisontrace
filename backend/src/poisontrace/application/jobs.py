from contextlib import nullcontext
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import re

from poisontrace.application.principals import Principal, principal_scope
from poisontrace.application.runs import require_run_analyst
from poisontrace.application.ports import JobStore
from poisontrace.domain import Scenario, SyntheticCase, ToolDefinition


class JobService:
    def __init__(self, store: JobStore, runs, groups=None, *, campaigns=None, profile="local"):
        self.store, self.runs, self.groups, self.profile = store, runs, groups, profile
        self.campaigns = campaigns

    def submit(self, intent, payload):
        owner = require_run_analyst()
        if not isinstance(intent, str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,128}', intent):
            raise ValueError('a valid submission intent is required')
        if not isinstance(payload, dict):
            raise ValueError('invalid execution request')
        workflow = payload.get('workflow', 'mcp-investigation-v1')
        allowed = {'workflow', 'provider', 'model', 'credential_id', 'mode', 'session_id'}
        allowed.update({'scenario_id'} if workflow == 'metadata-v1' else {'case_id', 'attack_family'})
        if not isinstance(payload, dict) or set(payload) - allowed:
            raise ValueError('invalid investigation request')
        if any(not isinstance(v, str) or len(v.encode()) > 200 for v in payload.values()):
            raise ValueError('investigation fields must be strings of at most 200 bytes')
        if workflow not in ('mcp-investigation-v1', 'metadata-v1'):
            raise ValueError('invalid investigation workflow')
        encoded = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        fingerprint = hashlib.sha256(encoded.encode()).hexdigest()
        existing = self.store.find_intent(owner, intent, fingerprint)
        if existing is not None:
            return existing
        if workflow == 'metadata-v1':
            scenario, mode, configuration = self.runs.prepare_metadata(payload)
            snapshot = dict(kind='metadata', scenario=asdict(scenario), mode=mode.value,
                            configuration=configuration, request=payload)
            self.check_metadata_size(snapshot)
        else:
            case, configuration, _ = self.runs.prepare_investigation(payload)
            snapshot = {'case': asdict(case), 'configuration': configuration, 'request': payload}
        return self.store.admit(owner, intent, fingerprint, snapshot)

    def get(self, identifier):
        return self.store.get(identifier, require_run_analyst())

    def list(self):
        return self.store.list(require_run_analyst())

    def execute_claim(self, claim, attempt_context=nullcontext):
        if claim['snapshot'].get('kind') == 'group':
            return self.execute_group(claim, attempt_context)
        if claim['snapshot'].get('kind') == 'campaign':
            return self.execute_campaign(claim, attempt_context)
        with attempt_context():
            return self.execute_single(claim)

    def execute_single(self, claim):
        self.store.begin_attempt(claim)
        with principal_scope(Principal(claim['owner_id'], 'analyst')):
            snapshot = claim['snapshot']
            if snapshot.get('kind') == 'metadata':
                configuration = dict(snapshot['configuration'], job_id=claim['job_id'], job_claim=claim['claim'])
                return self.runs.run_metadata(self.restore_scenario(snapshot['scenario']), snapshot['mode'], configuration, snapshot['request'].get('model'))
            case = SyntheticCase(**snapshot['case'])
            _, configuration, factory = self.runs.prepare_investigation(snapshot['request'], case=case)
            configuration.update(job_id=claim['job_id'], job_claim=claim['claim'])
            return self.runs.investigations.run_snapshot(case, configuration, model_factory=factory)

    @staticmethod
    def restore_scenario(snapshot):
        values = dict(snapshot)
        for field in ('tools', 'approved_tools'):
            if values[field] is not None:
                values[field] = tuple(ToolDefinition(**tool) for tool in values[field])
        return Scenario(**values)

    def submit_campaign(self, intent, identifier, ordinal=None, *, acknowledged=None):
        owner = require_run_analyst()
        self.campaigns.authorize(identifier)
        if not isinstance(intent, str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,128}', intent):
            raise ValueError('a valid submission intent is required')
        fingerprint = hashlib.sha256(json.dumps(['campaign', identifier, ordinal]).encode()).hexdigest()
        existing = self.store.find_intent(owner, intent, fingerprint)
        if existing is not None:
            return existing
        configuration, attempts, exclusions = self.campaigns.prepare_execution(identifier, ordinal)
        if acknowledged is not None and any(name not in acknowledged for name in exclusions.values()):
            raise ValueError('Repair or acknowledge excluded campaign files: ' + ', '.join(exclusions.values()))
        snapshot = dict(kind='campaign', ordinal=ordinal, configuration=configuration, attempts=attempts, exclusions=exclusions)
        self.check_metadata_size(snapshot)
        return self.store.admit_campaign(owner, intent, fingerprint, snapshot)

    @staticmethod
    def check_metadata_size(snapshot):
        if len(json.dumps(snapshot).encode()) > 256 * 1024:
            raise ValueError('metadata execution inputs exceed the size limit')

    def execute_campaign(self, claim, attempt_context):
        self.store.begin_attempt(claim)
        snapshot = claim['snapshot']
        with principal_scope(Principal(claim['owner_id'], 'analyst')):
            for index, scenario in snapshot['attempts'].items():
                with attempt_context():
                    self.store.start_campaign_attempt(claim, int(index))
                    configuration = dict(snapshot['configuration'], job_id=claim['job_id'], job_claim=claim['claim'], campaign_ordinal=index)
                    self.runs.run_metadata(self.restore_scenario(scenario), 'poisoned', configuration, configuration['model'])

    def submit_group(self, intent, payload, identifier=None):
        owner = require_run_analyst()
        if identifier is not None:
            self.groups.authorize(identifier)
        if not isinstance(intent, str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,128}', intent):
            raise ValueError('a valid submission intent is required')
        if not isinstance(payload, dict):
            raise ValueError('invalid group submission')
        for key, value in payload.items():
            if key == 'repeats':
                if type(value) is not int or value < 1:
                    raise ValueError('invalid repeat count')
            elif key == 'conditions':
                if not isinstance(value, list) or not 1 <= len(value) <= 3 or any(type(c) is not str or c not in ('clean', 'poisoned', 'defended') for c in value) or len(set(value)) != len(value):
                    raise ValueError('invalid condition schedule')
            elif not isinstance(value, str) or len(value.encode()) > 200:
                raise ValueError('invalid group field')
        fingerprint = hashlib.sha256(json.dumps(dict(kind='group', group_id=identifier, request=payload), sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        existing = self.store.find_intent(owner, intent, fingerprint)
        if existing is not None:
            return existing
        if identifier is None:
            self.check_schedule(payload)
            plan = self.groups.prepare_plan(payload)
        else:
            if set(payload) - {'credential_id'}:
                raise ValueError('reruns accept only a credential reference')
            plan = self.groups.store.get(identifier)['plan']
            self.check_schedule(plan)
            self.prepare_group(plan, payload)
        snapshot = dict(kind='group', plan=plan, credential_id=payload.get('credential_id'), intent=intent)
        return self.store.admit_group(owner, intent, fingerprint, snapshot, identifier)

    def check_schedule(self, plan):
        if self.profile == 'hosted' and (plan.get('repeats') != 1 or not isinstance(plan.get('conditions'), list) or not 1 <= len(plan['conditions']) <= 3):
            raise ValueError('hosted groups allow one repeat and at most three unique conditions')

    def prepare_group(self, plan, payload):
        from poisontrace.domain import investigation_attack
        if plan['execution'] != self.groups.profile(plan['provider']) or (plan['attack'] and plan['attack'] != asdict(investigation_attack(plan['attack']['family']))):
            raise ValueError('runtime or payload changed; create a new group for the new inputs')
        case = SyntheticCase(**plan['case'])
        prepared = {}
        for condition in plan['conditions']:
            request = dict(case_id=case.case_id, mode=condition, provider=plan['provider'], model=plan['model'])
            if payload.get('credential_id'):
                request['credential_id'] = payload['credential_id']
            if condition != 'clean':
                request['attack_family'] = plan['attack']['family']
            prepared[condition] = self.runs.prepare_investigation(request, case=case)
        return prepared

    def execute_group(self, claim, attempt_context):
        self.check_schedule(claim['snapshot']['plan'])
        self.store.begin_attempt(claim)
        with principal_scope(Principal(claim['owner_id'], 'analyst')):
            snapshot = claim['snapshot']
            prepared = self.prepare_group(snapshot['plan'], snapshot)
            for attempt in snapshot['attempts']:
                with attempt_context():
                    self.store.start_group_attempt(claim, attempt['attempt'])
                    case, configuration, factory = prepared[attempt['condition']]
                    configuration = {**configuration, 'job_id':claim['job_id'], 'job_claim':claim['claim'],
                                     'group_id':snapshot['group_id'], 'group_attempt':str(attempt['attempt']), 'group_repeat':str(attempt['repeat'])}
                    self.runs.investigations.run_snapshot(deepcopy(case), configuration, model_factory=factory)
            return self.groups.get(snapshot['group_id'])
