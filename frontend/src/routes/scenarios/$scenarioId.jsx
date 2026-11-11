import { ScenarioEditor } from "../../features/scenarios/ScenarioFeaturePages";

export function ScenarioDetailRoute({ scenarioId, ...props }) {
  return <ScenarioEditor {...props} scenarioId={scenarioId} isNew={false} />;
}
