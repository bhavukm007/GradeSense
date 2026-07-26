import type {
  Correlations,
  DatasetStatistics,
  Health,
  Alert,
  Drift,
  Feedback,
  LiveMetrics,
  ModelInfo,
  Paginated,
  Prediction,
  PredictionHistoryItem,
  ProcessInput,
  RecommendationHistoryItem,
  RecommendationResponse,
  RollingMetric,
  StreamStatus,
  Forecast,
  ForecastSimulation,
  ForecastRecommendation,
  Effectiveness,
  RegisteredModel,
  RuntimeConfig,
  AuditEntry,
  AdminMetrics,
  AdminHealth,
  RecommendationOutcome,
  TrajectoryPoint,
  RelationshipDiscovery,
  DemoSeedResult,
} from './types'

const API_URL = (import.meta.env.VITE_API_URL ?? '').trim().replace(/\/$/, '')
if (!API_URL) {
  throw new Error('VITE_API_URL must be configured before building or starting GradeSense.')
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public details?: unknown,
  ) {
    super(message)
  }
}

async function request<T>(
  path: string,
  options?: RequestInit,
  timeoutMs = 12_000,
): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...options?.headers },
      signal: controller.signal,
    })
    const payload = await response.json().catch(() => null)
    if (!response.ok) {
      const message =
        payload?.error?.message ||
        (typeof payload?.detail === 'string' ? payload.detail : undefined) ||
        payload?.detail?.[0]?.msg ||
        `Request failed (${response.status})`
      throw new ApiError(message, response.status, payload)
    }
    return payload as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('The backend took too long to respond. Please try again.')
    }
    throw new ApiError('Unable to connect to the GradeSense backend.')
  } finally {
    window.clearTimeout(timeout)
  }
}

const post = <T>(path: string, body: ProcessInput) =>
  request<T>(path, { method: 'POST', body: JSON.stringify(body) })

export const api = {
  health: () => request<Health>('/health'),
  modelInfo: () => request<ModelInfo>('/model/info'),
  datasetStatistics: () => request<DatasetStatistics>('/dataset/statistics'),
  correlations: (limit = 20) => request<Correlations>(`/correlations?limit=${limit}`),
  relationshipDiscovery: (stage: 'early' | 'middle' | 'late', limit = 10) =>
    request<RelationshipDiscovery>(
      `/relationships/discovery?stage=${stage}&min_strength=0.1&limit=${limit}`,
      undefined,
      60_000,
    ),
  seedDemo: () => request<DemoSeedResult>('/demo/seed', { method: 'POST' }, 180_000),
  predict: (values: ProcessInput) => post<Prediction>('/predict', values),
  recommend: (values: ProcessInput) => post<RecommendationResponse>('/recommend', values),
  predictionHistory: (page: number, pageSize = 20) =>
    request<Paginated<PredictionHistoryItem>>(
      `/history/predictions?page=${page}&page_size=${pageSize}`,
    ),
  recommendationHistory: (page: number, pageSize = 20) =>
    request<Paginated<RecommendationHistoryItem>>(
      `/history/recommendations?page=${page}&page_size=${pageSize}`,
    ),
  alerts: () => request<Alert[]>('/alerts?limit=50'),
  acknowledgeAlert: (id: string) => request<Alert>(`/alerts/${id}/acknowledge`, { method: 'POST' }),
  streamStatus: () => request<StreamStatus>('/stream/status'),
  liveMetrics: () => request<LiveMetrics>('/metrics/live'),
  rollingMetrics: () => request<RollingMetric[]>('/metrics/rolling'),
  drift: () => request<Drift | null>('/drift'),
  feedback: () => request<Feedback[]>('/feedback'),
  createFeedback: (body: { prediction_id: string; outcome: string; notes?: string }) =>
    request<Feedback>('/feedback', { method: 'POST', body: JSON.stringify(body) }),
  forecastHistory: () => request<{ items: Forecast[]; total: number }>('/forecast/history'),
  simulateForecast: (body: {
    forecast_id: string
    changes: { variable: string; value: number }[]
  }) =>
    request<ForecastSimulation>('/forecast/simulate', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  generateInterventions: (body: {
    forecast_id: string
    max_results?: number
    max_variables?: number
  }) =>
    request<ForecastRecommendation[]>('/interventions/recommendations', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  interventionHistory: () => request<ForecastRecommendation[]>('/interventions/recommendations'),
  decideRecommendation: (
    id: string,
    body: {
      operator_action: 'accepted' | 'rejected' | 'modified' | 'delayed' | 'applied'
      reason?: string
      modified_values?: Record<string, number>
      delay_duration_seconds?: number
      notes?: string
    },
  ) =>
    request(`/interventions/recommendations/${id}/decisions`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  interventionEffectiveness: () => request<Effectiveness>('/interventions/effectiveness'),
  evaluateRecommendationOutcome: (id: string, body: { observations: TrajectoryPoint[] }) =>
    request<RecommendationOutcome>(`/interventions/recommendations/${id}/outcome`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  registeredModels: () => request<RegisteredModel[]>('/models'),
  promoteModel: (model_id: string) =>
    request<RegisteredModel>('/models/promote', {
      method: 'POST',
      body: JSON.stringify({ model_id }),
    }),
  archiveModel: (model_id: string) =>
    request<RegisteredModel>('/models/archive', {
      method: 'POST',
      body: JSON.stringify({ model_id }),
    }),
  adminMetrics: () => request<AdminMetrics>('/admin/metrics'),
  adminHealth: () => request<AdminHealth>('/admin/health'),
  adminAudit: () => request<AuditEntry[]>('/admin/audit'),
  adminConfig: () => request<RuntimeConfig>('/admin/config'),
  updateAdminConfig: (body: RuntimeConfig) =>
    request<RuntimeConfig>('/admin/config', {
      method: 'PUT',
      body: JSON.stringify(body),
    }),
  exportCatalog: () =>
    request<{ resource: string; formats: string[]; row_count: number }[]>('/admin/exports'),
  createExport: async (resource: string, format: 'json' | 'csv') => {
    const response = await fetch(`${API_URL}/admin/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resource, format }),
    })
    if (!response.ok) throw new ApiError(`Export failed (${response.status})`)
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `gradesense-${resource}.${format}`
    link.click()
    URL.revokeObjectURL(url)
  },
}

export const websocketUrl = () => {
  const url = new URL(API_URL)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.pathname = '/ws/dashboard'
  return url.toString()
}
