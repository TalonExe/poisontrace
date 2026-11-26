import React from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, XAxis, YAxis } from "recharts";

export default function SavedAttemptsPlot({ buckets, series, onNavigate }) {
  const tick = { fill: "var(--ec-text-muted)", fontSize: 12 };

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={buckets} margin={{ top: 4, right: 8, left: 0, bottom: 0 }} accessibilityLayer={false}>
        <CartesianGrid vertical={false} stroke="var(--ec-border)" />
        <XAxis dataKey="label" tick={tick} tickLine={false} axisLine={{ stroke: "var(--ec-border-strong)" }} />
        <YAxis allowDecimals={false} width={32} tick={tick} tickLine={false} axisLine={false} />
        {series.map(({ metric, fill }) => (
          <Bar key={metric} dataKey={metric} stackId="attempts" fill={fill} maxBarSize={54} isAnimationActive={false}
            shape={({ x, y, width, height, payload }) => {
              const result = payload.results[metric];
              if (!result) return null;
              return (
                <rect x={x} y={y} width={width} height={height} fill={fill} className="activity-attempt-bar"
                  aria-label={result.label} onClick={() => onNavigate(result.href)}>
                  <title>{result.label}</title>
                </rect>
              );
            }}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
