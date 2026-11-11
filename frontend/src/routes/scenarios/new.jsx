import { ScenarioEditor } from "../../features/scenarios/ScenarioFeaturePages";

export function NewScenarioRoute(props) {
  return <ScenarioEditor {...props} isNew />;
}
