import { cleanup, fireEvent, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '../api/client'
import { Sidebar } from '../components/layout/Sidebar'
import { renderApp } from '../test/render'
import { PredictionPage } from './PredictionPage'
import { RecommendationsPage } from './RecommendationsPage'
import { NotFoundPage } from './NotFoundPage'

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
        },
        {
          text: 'Increase steam pressure.',
          confidence: 0.72,
          expected_improvement: 2.1,
          affected_variables: ['steam_pressure'],
        },
      ],
      created_at: prediction.created_at,
    })
    renderApp(<RecommendationsPage />)
    await userEvent.click(screen.getByRole('button', { name: 'Generate recommendations' }))
    expect(await screen.findByText('Reduce machine speed.')).toBeInTheDocument()
    expect(screen.getByText('Increase steam pressure.')).toBeInTheDocument()
  })

  it('shows API connection errors', async () => {
    vi.spyOn(api, 'predict').mockRejectedValue(new Error('Backend unavailable'))
    renderApp(<PredictionPage />)
    await userEvent.click(screen.getByRole('button', { name: 'Run transition prediction' }))
    expect(await screen.findByText('Backend unavailable')).toBeInTheDocument()
  })

  it('renders navigation and the 404 page', () => {
    renderApp(<Sidebar open onClose={() => undefined} />)
    expect(screen.getByRole('link', { name: 'Prediction Center' })).toHaveAttribute(
      'href',
      '/prediction',
    )
    cleanup()
    renderApp(<NotFoundPage />)
    expect(screen.getByText('Workspace not found')).toBeInTheDocument()
  })
})
