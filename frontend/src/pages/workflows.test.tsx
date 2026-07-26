import { cleanup, fireEvent, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '../api/client'
import { Sidebar } from '../components/layout/Sidebar'
import { renderApp } from '../test/render'
import { PredictionPage } from './PredictionPage'
import { RecommendationsPage } from './RecommendationsPage'
import { NotFoundPage } from './NotFoundPage'
import { RecommendationHistoryPage } from './RecommendationHistoryPage'

const prediction = {
  prediction_id: 'prediction-1',
  quality_score: 91.2,
  off_spec_probability: 0.08,
  expected_stabilization_time: 22,
  model_version: 'rf-test',
  explanation: {
    summary: 'Moisture is the leading transition influence.',
    top_contributing_features: [
      {
        feature: 'moisture',
        value: 7.4,
        contribution: -0.2,
        importance: 0.3,
        direction: 'negative',
      },
    ],
    feature_importance: { moisture: 0.3, machine_speed: 0.2 },
  },
  created_at: '2026-07-25T12:00:00Z',
}

describe('operator workflows', () => {
  beforeEach(() => {
    vi.spyOn(api, 'predict').mockResolvedValue(prediction)
  })

  it('submits every process field and renders the prediction explanation', async () => {
    const predict = vi.spyOn(api, 'predict').mockResolvedValue(prediction)
    renderApp(<PredictionPage />)
    expect(screen.getByLabelText(/Machine Speed/)).toBeInTheDocument()
    fireEvent.submit(
      screen.getByRole('button', { name: 'Run transition prediction' }).closest('form')!,
    )
    await waitFor(() => expect(predict).toHaveBeenCalled())
    expect(await screen.findByText('91.2 / 100')).toBeInTheDocument()
    expect(screen.getByText('Moisture is the leading transition influence.')).toBeInTheDocument()
  })

  it('renders multiple model-evaluated recommendations', async () => {
    vi.spyOn(api, 'recommend').mockResolvedValue({
      recommendation_id: 'recommendation-1',
      prediction,
      recommendations: [
        {
          text: 'Reduce machine speed.',
          confidence: 0.82,
          expected_improvement: 4.2,
          affected_variables: ['machine_speed'],
          inference_sources: ['Forecast', 'Correlation Analysis'],
        },
        {
          text: 'Increase steam pressure.',
          confidence: 0.72,
          expected_improvement: 2.1,
          affected_variables: ['steam_pressure'],
          inference_sources: ['Forecast', 'Correlation Analysis'],
        },
      ],
      created_at: prediction.created_at,
    })
    renderApp(<RecommendationsPage />)
    await userEvent.click(screen.getByRole('button', { name: 'Generate recommendations' }))
    expect(await screen.findByText('Reduce machine speed.')).toBeInTheDocument()
    expect(screen.getByText('Increase steam pressure.')).toBeInTheDocument()
    expect(screen.getAllByText('Forecast')).toHaveLength(2)
  })

  it('shows API connection errors', async () => {
    vi.spyOn(api, 'predict').mockRejectedValue(new Error('Backend unavailable'))
    renderApp(<PredictionPage />)
    await userEvent.click(screen.getByRole('button', { name: 'Run transition prediction' }))
    expect(await screen.findByText('Backend unavailable')).toBeInTheDocument()
  })

  it('submits observed values and displays recommendation effectiveness', async () => {
    const trajectory = [1, 2, 3].map((step) => ({
      step,
      timestamp: `2026-07-25T12:0${step}:00Z`,
      basis_weight: 80 + step,
      lower_bound: 78 + step,
      upper_bound: 82 + step,
      deviation_pct: step,
      lower_spec_limit: 78,
      upper_spec_limit: 82,
    }))
    vi.spyOn(api, 'recommendationHistory').mockResolvedValue({
      items: [],
      pagination: { page: 1, page_size: 20, total: 0, total_pages: 1 },
    })
    vi.spyOn(api, 'interventionHistory').mockResolvedValue([
      {
        recommendation_id: 'forecast-recommendation-1',
        forecast_id: 'forecast-1',
        state: 'accepted',
        rank: 1,
        affected_variables: ['machine_speed'],
        current_values: { machine_speed: 940 },
        changes: [{ variable: 'machine_speed', value: 900 }],
        baseline_trajectory: trajectory,
        intervention_trajectory: trajectory,
        metrics: {
          crossing_probability_before: 0.7,
          crossing_probability_after: 0.2,
          predicted_peak_deviation_before: 4.1,
          predicted_peak_deviation_after: 1.2,
          predicted_stabilization_time_before: 8,
          predicted_stabilization_time_after: 4,
          estimated_improvement: 0.5,
          crossing_avoided: true,
          crossing_delay_steps: null,
        },
        confidence: 0.82,
        constraint_validation: {
          feasible: true,
          checks: [],
          violations: [],
          recipe_rules: [],
        },
        explanation: {
          selection_reason: 'Best forecast improvement.',
          forecast_causes: ['machine speed'],
          trajectory_effect: 'Reduces peak deviation.',
          expected_risks: [],
          remaining_uncertainty: 'Model uncertainty remains.',
          recipe_attribution: [],
        },
        inference_sources: ['Forecast', 'Historical Trend'],
        historical_evidence: {
          similar_transition_count: 3,
          historical_acceptance_rate: 0.67,
          historical_effectiveness: 0.81,
        },
        created_at: '2026-07-25T12:00:00Z',
        updated_at: '2026-07-25T12:05:00Z',
        expires_at: null,
      },
    ])
    vi.spyOn(api, 'interventionEffectiveness').mockResolvedValue({
      evaluated_count: 0,
      crossing_avoidance_rate: 0,
      crossing_delay_rate: 0,
      mean_prediction_error: 0,
      mean_deviation_improvement: 0,
      mean_stabilization_improvement: 0,
    })
    const decide = vi.spyOn(api, 'decideRecommendation').mockResolvedValue({})
    const evaluate = vi.spyOn(api, 'evaluateRecommendationOutcome').mockResolvedValue({
      outcome_id: 'outcome-1',
      recommendation_id: 'forecast-recommendation-1',
      metrics: {
        prediction_accuracy: 0.98,
        recommendation_accuracy: 0.91,
        crossing_avoided: true,
        crossing_delayed: false,
        stabilization_improvement: 4,
        actual_vs_predicted_deviation: 0.2,
        deviation_improvement: 2.8,
      },
      evaluated_at: '2026-07-25T12:30:00Z',
    })

    renderApp(<RecommendationHistoryPage />)
    await userEvent.click(await screen.findByText('Evaluate outcome'))
    await userEvent.clear(screen.getByLabelText('Actual Basis Weight at step 1'))
    await userEvent.type(screen.getByLabelText('Actual Basis Weight at step 1'), '80.5')
    await userEvent.type(
      screen.getByPlaceholderText('Describe the applied change and observed process response'),
      'Machine speed change applied successfully.',
    )
    await userEvent.click(screen.getByRole('button', { name: 'Submit observed outcome' }))

    await waitFor(() => expect(evaluate).toHaveBeenCalled())
    expect(decide).toHaveBeenCalledWith(
      'forecast-recommendation-1',
      expect.objectContaining({
        operator_action: 'applied',
        notes: 'Machine speed change applied successfully.',
      }),
    )
    expect(await screen.findByText('Outcome evaluation complete')).toBeInTheDocument()
    expect(screen.getByText('98%')).toBeInTheDocument()
    expect(screen.getByText(/Machine speed change applied successfully/)).toBeInTheDocument()
  })

  it('renders navigation and the 404 page', () => {
    renderApp(<Sidebar open onClose={() => undefined} />)
    expect(screen.getByRole('link', { name: 'Prediction Center' })).toHaveAttribute(
      'href',
      '/prediction',
    )
    expect(screen.getByRole('link', { name: 'Demo Workspace' })).toHaveAttribute(
      'href',
      '/demo-workspace',
    )
    cleanup()
    renderApp(<NotFoundPage />)
    expect(screen.getByText('Workspace not found')).toBeInTheDocument()
  })
})
