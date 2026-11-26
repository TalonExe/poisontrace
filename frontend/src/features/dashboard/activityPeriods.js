export function localDate(date, days = 0) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + days);
}

export function activityPeriod(date, mode, offset = 0) {
  if (mode === "month") {
    return {
      start: new Date(date.getFullYear(), date.getMonth() + offset, 1),
      end: new Date(date.getFullYear(), date.getMonth() + offset + 1, 1),
    };
  }
  const monday = localDate(date, offset * 7 - (date.getDay() + 6) % 7);
  return { start: monday, end: localDate(monday, 7) };
}

export function activityRange(start, end) {
  const format = new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" });
  return format.formatRange(start, localDate(end, -1));
}

export function activityLink(view, start, end, metric, value) {
  const filter = new URLSearchParams({ start: +start / 1000, end: +end / 1000, metric });
  if (value) filter.set("value", value);
  return `/results/${view}?${filter}`;
}

export function readActivityFilter(search, view) {
  const params = new URLSearchParams(search);
  const metric = params.get("metric");
  const value = params.get("value");
  if (!(view === "runs" ? ["attempts", "provider"] : view === "groups" ? ["groups", "reruns"] : []).includes(metric)) return null;
  if (!/^-?\d+$/.test(params.get("start") ?? "") || !/^-?\d+$/.test(params.get("end") ?? "")) return null;
  const start = Number(params.get("start"));
  const end = Number(params.get("end"));
  if (start < -62135596800 || end > 253402300799 || end <= start || end - start > 32 * 86400) return null;
  return { start, end, metric, value };
}

export function providerLabel(provider) {
  return { openai: "OpenAI", gemini: "Gemini", scripted: "Scripted", unknown: "Unknown" }[provider] ?? provider;
}
