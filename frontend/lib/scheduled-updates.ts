export type UpdateSchedule = { connector_id: number; connector_name: string; connector_status: string; authority: { domain: string; mode: string }[]; interval_minutes: number; stale_after_minutes: number; enabled: boolean; version: number; next_due_at: string | null; due: boolean; last_success_at: string | null; freshness: string; last_attempt_at: string | null; last_attempt_status: string; last_attempt_reason: string };
export type UpdateSchedules = { can_edit: boolean; worker_status: string; worker_reason: string; freshness_basis: string; schedules: UpdateSchedule[] };
export function validateSchedule(interval: number, stale: number) {
  if (!Number.isInteger(interval) || interval < 5 || interval > 10080) throw new Error("Choose an update interval between 5 and 10,080 whole minutes.");
  if (!Number.isInteger(stale) || stale < interval || stale > 20160) throw new Error("The old-data alert must be at least the update interval and at most 20,160 whole minutes.");
}
export function fictionalSchedules(): UpdateSchedules {
  return { can_edit: true, worker_status: "FICTIONAL_EXAMPLE", worker_reason: "These are example settings for this visit. No background worker or bank connection is running.", freshness_basis: "Fictional missing-data example; no collected company records.", schedules: [{ connector_id: 1, connector_name: "Example bank feed", connector_status: "ACTIVE", authority: [{ domain: "BANK_BALANCES", mode: "SHADOW" }], interval_minutes: 60, stale_after_minutes: 120, enabled: false, version: 0, next_due_at: null, due: false, last_success_at: null, freshness: "MISSING", last_attempt_at: null, last_attempt_status: "NOT_ATTEMPTED", last_attempt_reason: "Example only. No data was collected." }] };
}
