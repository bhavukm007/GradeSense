import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '../api/client'
import type { Forecast, ForecastRecommendation } from '../api/types'
import { renderApp } from '../test/render'
import { DemoWorkspacePage } from './DemoWorkspacePage'

const trajectory = [1, 2, 3].map((step) => ({
  step,
  timestamp: `2026-07-27T00:0${step}:00Z`,
  basis_weight: 80 + step,
  lower_bound: 78 + step,
  upper_bound: 82 + step,
  deviation_pct: step / 10,
  lower_spec_limit: 78,
  upper_spec_limit: 82,
}))

const forecast = (forecastId: string, transitionId: string): Forecast => ({
  forecast_id: forecastId,
  transition_id: transitionId,
  model_version: 'forecast-test',
  history_window: 20,
  forecast_horizon: 3,
  confidence: 0.9,
  trajectory,
  specification: {
    target_basis_weight: 80,
    lower_spec_limit: 78,
    upper_spec_limit: 82,
    current_deviation_pct: 0.2,
    maximum_predicted_deviation_pct: 1.2,
    crossing_probability: 0.1,
    predicted_crossing_step: null,
    predicted_crossing_time: null,
    remaining_safe_operating_seconds: null,
    predicted_stabilization_step: 2,
  },
  top_influencing_variables: [['machine_speed', 0.5]],
  explanation: 'Forecast remains inside the specification.',
  created_at: '2026-07-27T00:00:00Z',
})

const recommendation = (
  recommendationId: string,
  forecastId: string,
  selectionReason: string,
): ForecastRecommendation => ({
  recommendation_id: recommendationId,
  forecast_id: forecastId,
  state: 'proposed',
  rank: 1,
  affected_variables: ['machine_speed'],
  current_values: { machine_speed: 900 },
  changes: [{ variable: 'machine_speed', value: 880 }],
  baseline_trajectory: trajectory,
  intervention_trajectory: trajectory,
  metrics: {
    crossing_probability_before: 0.5,
    crossing_probability_after: 0.2,
    predicted_peak_deviation_before: 2,
    predicted_peak_deviation_after: 1,
    predicted_stabilization_time_before: 6,
    predicted_stabilization_time_after: 3,
    estimated_improvement: 0.4,
    crossing_avoided: true,
    crossing_delay_steps: null,
  },
  confidence: 0.9,
  constraint_validation: {
    feasible: true,
    checks: [],
    violations: [],
    recipe_rules: [],
  },
  explanation: {
    selection_reason: selectionReason,
    forecast_causes: ['machine speed'],
    trajectory_effect: 'Reduces forecast deviation.',
    expected_risks: [],
    remaining_uncertainty: 'Normal forecast uncertainty.',
    recipe_attribution: [],
  },
  inference_sources: ['Forecast'],
  historical_evidence: {
    similar_transition_count: 1,
    historical_acceptance_rate: 1,
    historical_effectiveness: 0.9,
  },
  created_at: '2026-07-27T00:00:00Z',
  updated_at: '2026-07-27T00:00:00Z',
  expires_at: null,
})

describe('Demo Workspace recommendations', () => {
  beforeEach(() => {
    class IntersectionObserver {
      observe() {}
      disconnect() {}
    }
    vi.stubGlobal('IntersectionObserver', IntersectionObserver)
    vi.spyOn(api, 'health').mockResolvedValue({
      status: 'healthy',
      service: 'gradesense',
      version: '0.2.0',
      environment: 'test',
    })
    vi.spyOn(api, 'interventionEffectiveness').mockResolvedValue({
      evaluated_count: 0,
      crossing_avoidance_rate: 0,
      crossing_delay_rate: 0,
      mean_prediction_error: 0,
      mean_deviation_improvement: 0,
      mean_stabilization_improvement: 0,
    })
    vi.spyOn(api, 'liveMetrics').mockResolvedValue({
      sensor: null,
      prediction: null,
      recommendations: [],
      alerts: [],
      drift: null,
      updated_at: null,
    })
    vi.spyOn(api, 'relationshipDiscovery').mockResolvedValue({
      relationships: [],
      method: 'all',
      max_lag: 12,
      record_count: 0,
    })
  })

  it('automatically displays seeded recommendations for the demo forecast', async () => {
    vi.spyOn(api, 'forecastHistory').mockResolvedValue({
      items: [forecast('live-forecast', 'LIVE-1'), forecast('demo-forecast', 'DEMO-1')],
      total: 2,
    })
    vi.spyOn(api, 'interventionHistory').mockResolvedValue([
      recommendation('seeded-recommendation', 'demo-forecast', 'Existing demo recommendation.'),
    ])

    renderApp(<DemoWorkspacePage />)

    expect(await screen.findByText('Existing demo recommendation.')).toBeInTheDocument()
    expect(screen.queryByText('No recommendations yet.')).not.toBeInTheDocument()
  })

  it('writes generated recommendations into the visible query cache', async () => {
    vi.spyOn(api, 'forecastHistory').mockResolvedValue({
      items: [forecast('demo-forecast', 'DEMO-1')],
      total: 1,
    })
    vi.spyOn(api, 'interventionHistory').mockResolvedValue([])
    const generate = vi.spyOn(api, 'generateInterventions').mockResolvedValue([
      recommendation('generated-recommendation', 'demo-forecast', 'Generated recommendation.'),
    ])

    renderApp(<DemoWorkspacePage />)
    await userEvent.click(
      await screen.findByRole('button', { name: 'Generate ranked recommendations' }),
    )

    await waitFor(() =>
      expect(generate).toHaveBeenCalledWith({
        forecast_id: 'demo-forecast',
        max_results: 5,
        max_variables: 2,
      }),
    )
    expect(await screen.findByText('Generated recommendation.')).toBeInTheDocument()
    expect(screen.queryByText('No recommendations yet.')).not.toBeInTheDocument()
  })

  it('clears an auxiliary history error after recommendation generation succeeds', async () => {
    vi.spyOn(api, 'forecastHistory').mockResolvedValue({
      items: [forecast('demo-forecast', 'DEMO-1')],
      total: 1,
    })
    vi.spyOn(api, 'interventionHistory').mockRejectedValue(
      new Error('Unable to connect to the GradeSense backend.'),
    )
    vi.spyOn(api, 'generateInterventions').mockResolvedValue([
      recommendation('generated-recommendation', 'demo-forecast', 'Recovered recommendation.'),
    ])

    renderApp(<DemoWorkspacePage />)

    expect(
      await screen.findByText(
        'Saved recommendation history is temporarily unavailable. You can still generate new recommendations.',
      ),
    ).toBeInTheDocument()
    expect(screen.queryByText('Unable to connect to the GradeSense backend.')).not.toBeInTheDocument()

    await userEvent.click(
      screen.getByRole('button', { name: 'Generate ranked recommendations' }),
    )

    expect(await screen.findByText('Recovered recommendation.')).toBeInTheDocument()
    expect(
      screen.queryByText(
        'Saved recommendation history is temporarily unavailable. You can still generate new recommendations.',
      ),
    ).not.toBeInTheDocument()
    expect(screen.queryByText('Unable to connect to the GradeSense backend.')).not.toBeInTheDocument()
  })
})
