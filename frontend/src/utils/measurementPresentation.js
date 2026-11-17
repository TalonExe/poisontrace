export function formatRate(rate) {
  if (!rate) return 'Not applicable';
  const value = rate.denominator && rate.value != null ? `${(rate.value * 100).toFixed(1)}%` : 'Not applicable';
  return `${value} (${rate.numerator}/${rate.denominator})`;
}
