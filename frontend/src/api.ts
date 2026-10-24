export type Metrics = { status: string; mae_mw: number | null; rmse_mw: number | null; bias_mw: number | null; matched_count: number; expected_count: number; coverage_percent: number | null; positive_count: number; negative_count: number; zero_count: number }
export type Observation = {start_time: string; forecast_mw: number | null; publish_time: string | null; forecast_conflict: boolean; forecast_age_hours: number | null; lead_time_hours: number | null; actual_mw?: number | null; actual_conflict?: boolean; signed_error_mw?: number | null; absolute_error_mw?: number | null}
export type Day = {decision_date: string; delivery_date: string; decision_timestamp: string; cutoff: string; timezone: string; context: string; evaluation_resolution_minutes: number; alignment_policy: string; coverage: Record<string, number>; observations: Observation[]; metrics: Metrics | null}
export type Accuracy = {from_date: string; to_date: string; cutoff: string; metrics: Metrics; daily: Day[]}
export type Metadata = {default_cutoff: string; timezone: string; evaluation_resolution_minutes: number; actual_interval_minutes: number; alignment_policy: string; alignment_limitation: string; coverage_denominator: string; assumptions: string[]; snapshot: {snapshot_id: string; retrieved_at: string; row_counts: Record<string,number>; quality: Record<string,Record<string,number>>; coverage: Record<string,{first_target:string;last_target:string}>; limitations:string[]; requests: {url:string}[]}}
export type Vintages = {start_time: string; vintages: {start_time:string;publish_time:string;generation_mw:number|null;conflict:boolean}[]}
const base = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
export async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  let response: Response
  try { response = await fetch(`${base}/api/v1/${path}`, {signal}) } catch (error) {
    if ((error as Error).name === 'AbortError') throw error
    throw new Error('The backend is not reachable. Check that the API is running and try again.')
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(response.status === 503 ? 'The historical snapshot is unavailable. Restore or ingest the dataset, then restart the backend.' : typeof body.detail === 'string' ? body.detail : `The request could not be completed (${response.status}).`)
  }
  return response.json()
}
export const apiBase = base
