import { signal, computed } from "@preact/signals-react";

// The "Pulse" of the system
export const metrics = signal({
  tps: 0,
  latency: 0,
  tokenEfficiency: 0,
  queueSize: 0,
});

// Derived state for the UI
export const systemStatus = computed(() => {
  if (metrics.value.latency > 1000) return "⚠️ STRESSED";
  if (metrics.value.queueSize > 10) return "⚙️ COMPACTING";
  return "🟢 OPTIMAL";
});

// Actions
export const updateMetrics = (newData: Partial<typeof metrics.value>) => {
  metrics.value = { ...metrics.value, ...newData };
};

// Elicitation Queue Signal
export const elicitations = signal<any[]>([]);
export const addElicitation = (item: any) => {
  elicitations.value = [item, ...elicitations.value];
};
