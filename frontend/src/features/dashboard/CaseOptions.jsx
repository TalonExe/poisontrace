import React from "react";

const categories = [
  ["benign-activity", "Benign activity"],
  ["false-positive-alert", "False-positive alerts"],
  ["malicious-incident", "Malicious incidents"],
  ["uncategorized", "Uncategorized"],
];

export function CaseOptions({ cases, showCaseId = false }) {
  const groups = new Map(categories.map(([category]) => [category, []]));
  for (const item of cases) {
    const group = groups.get(item.dataset_category) ?? groups.get("uncategorized");
    group.push(item);
  }

  return categories.map(([category, label]) => {
    const items = groups.get(category);
    if (!items.length) return null;
    return (
      <optgroup key={category} label={label}>
        {items.map((item) => (
          <option key={item.case_id} value={item.case_id}>
            {item.name}{showCaseId ? ` · ${item.case_id}` : ""} · v{item.case_version}
          </option>
        ))}
      </optgroup>
    );
  });
}
