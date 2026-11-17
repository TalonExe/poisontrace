"""Pure matched comparisons. Ordinary metadata differences are the selected intervention."""
from copy import deepcopy
from poisontrace.domain.investigation_metrics import investigation_metrics


MODES = ('clean','poisoned','defended')


def incompatibilities(plan, attempt, result):
    reasons = []
    config, investigation = result.run_configuration, result.investigation or {}
    execution = plan['execution']
    condition = attempt['condition']
    if result.mode.value != condition or config.get('workflow') != 'mcp-investigation-v1':
        reasons.append('condition/workflow')
    if investigation.get('case_snapshot') != plan['case']:
        # JSON converts tuples to lists; the stored plan and result both use JSON.
        reasons.append('case version, evidence or targets')
    if config.get('provider') != plan['provider'] or result.model_name != plan['model']:
        reasons.append('provider/model')
    if result.prompt_version != execution['model']['prompt_version']:
        reasons.append('prompt version')
    if investigation.get('prompt_snapshot') != execution['model']['prompt_snapshot']:
        reasons.append('prompt snapshot')
    if investigation.get('model_settings') != execution['model']['settings']:
        reasons.append('model settings unavailable or changed')
    if result.scoring_version != execution['scoring_version'] or investigation.get('decision_contract_version') != execution['decision_contract_version']:
        reasons.append('scoring/decision version')
    if config.get('condition_version') != execution['condition_version'] or any(config.get(k)!=v for k,v in execution['limits'].items()):
        reasons.append('execution settings')
    if investigation.get('approved_manifest') != execution['approved_manifest']:
        reasons.append('approved definitions')
    expected_attack = plan['attack'] if condition != 'clean' else None
    if investigation.get('attack') != expected_attack:
        reasons.append('payload version or snapshot')
    policy = investigation.get('manifest',{})
    expected = deepcopy(execution['approved_manifest'])
    if expected_attack:
        for tool in expected:
            if tool['server_id']=='controlled-malicious' and tool['name']=='get_advisory':
                tool['description'] = expected_attack['description']
                tool['definition']['description'] = expected_attack['description']
    def ordered(tools):
        return sorted(tools, key=lambda t:(t['server_id'],t['name']))
    # Missing discovery on failures is unavailable policy evidence, not an invented mismatch.
    if policy.get('discovered') and ordered(policy['discovered']) != ordered(expected):
        reasons.append('unexpected discovered definitions')
    expected_exposed = execution['approved_manifest'] if condition=='clean' else expected if condition=='poisoned' else [t for t in expected if t in execution['approved_manifest']]
    if policy.get('discovered') and ordered(policy.get('exposed',[])) != ordered(expected_exposed):
        reasons.append('unexpected exposed definitions')
    if policy.get('enforced') is not (condition!='poisoned'):
        reasons.append('manifest enforcement')
    for observation in investigation.get('evidence',[]):
        if observation['server_id']=='trusted-soc' and observation['result'].get('records') != plan['case']['reads'].get(observation['tool_name']):
            reasons.append('returned evidence changed')
            break
    return reasons


def compare_group(group, results):
    plan = group['plan']
    eligible, excluded, missing = [], [], []
    for attempt in group['attempts']:
        result = results.get(attempt['run_id'])
        if result is None:
            missing.append(attempt['attempt'])
            continue
        reasons = incompatibilities(plan, attempt, result)
        config=result.run_configuration
        if config.get('group_id')!=group['group_id'] or config.get('group_attempt')!=str(attempt['attempt']) or config.get('group_repeat')!=str(attempt['repeat']):
            reasons.append('group attribution')
        if reasons:
            excluded.append(dict(attempt=attempt['attempt'],run_id=attempt['run_id'], reasons=reasons))
        else:
            eligible.append(result)
    metrics = investigation_metrics(eligible)
    for condition,row in metrics['by_condition'].items():
        slots = [a for a in group['attempts'] if a['condition']==condition]
        actual = [results[a['run_id']] for a in slots if a['run_id'] in results]
        compatible = [r for r in eligible if r.mode.value==condition]
        row.update(requested=plan['repeats'] if condition in plan['conditions'] else 0,
                   scheduled=len(slots), saved=len(actual), excluded=len(actual)-len(compatible),
                   missing=sum(a['run_id'] not in results for a in slots),
                   all_saved_error_rate=dict(numerator=sum(r.status=='failed' or r.system_error for r in actual),denominator=len(actual),value=sum(r.status=='failed' or r.system_error for r in actual)/len(actual) if actual else None),
                   saved_failed=sum(r.status=='failed' for r in actual),
                   duration=dict(count=len(compatible), mean_ms=sum(r.execution_time_ms for r in compatible)/len(compatible) if compatible else None),
                   errors=[dict(run_id=r.run_id,category=r.error_category) for r in actual if r.status=='failed'])
        for value in row.values():
            if isinstance(value,dict) and 'denominator' in value and value is not row['all_saved_error_rate']:
                value['unavailable'] = len(compatible)-value['denominator']
        # Preserve the common rate DTO; unavailable counts are separate and explicit.
        row['unavailable'] = {key:value.pop('unavailable') for key,value in row.items() if isinstance(value,dict) and 'unavailable' in value}
    return dict(**metrics, excluded_attempts=excluded, missing_attempts=missing,
                missing_conditions=[condition for condition in plan['conditions'] if not any(r.mode.value==condition for r in eligible)],
                not_requested_conditions=[condition for condition in MODES if condition not in plan['conditions']])
