import { act, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '../../api/client'
import { renderApp } from '../../test/render'
import { LiveMonitoring } from './LiveMonitoring'

class MockWebSocket {
  static instance: MockWebSocket
  onopen?: () => void
  onclose?: () => void
  onmessage?: (event: MessageEvent) => void

  constructor() {
    MockWebSocket.instance = this
  }

  close() {}

  emit(event: string, data: unknown) {
    this.onmessage?.({ data: JSON.stringify({ event, data }) } as MessageEvent)
  }
}

const process = {
  current_grade: 'Kraft',
  target_grade: 'CopyPaper',
  machine_speed: 880,
  steam_pressure: 5.4,
  dryer_temperature: 104,
  moisture: 7.4,
  basis_weight: 86,
  caliper: 112,
  pulp_consistency: 3.5,
  stock_flow: 3400,
  refining_energy: 160,
  headbox_pressure: 3.8,
  reel_tension: 5.2,
  ambient_temperature: 30,
  humidity: 72,
}

describe('live monitoring', () => {
  beforeEach(() => {
    vi.stubGlobal('WebSocket', MockWebSocket)
    vi.spyOn(api, 'liveMetrics').mockResolvedValue({
      sensor: null,
      prediction: null,
      recommendations: [],
      alerts: [],
      drift: null,
      updated_at: null,
    })
    vi.spyOn(api, 'streamStatus').mockResolvedValue({
      status: 'running',
      sample_count: 0,
      connected_clients: 1,
    })
    vi.spyOn(api, 'rollingMetrics').mockResolvedValue([])
    vi.spyOn(api, 'alerts').mockResolvedValue([])
  })

  it('updates live process values and prediction metrics from WebSocket events', async () => {
    renderApp(<LiveMonitoring />)
    await waitFor(() => expect(MockWebSocket.instance).toBeDefined())
    act(() => {
      MockWebSocket.instance.onopen?.()
      MockWebSocket.instance.emit('sensor_update', process)
      MockWebSocket.instance.emit('prediction', {
        prediction_id: 'live-1',
        quality_score: 88.4,
        off_spec_probability: 0.12,
        expected_stabilization_time: 31,
        model_version: 'rf-live',
        explanation: {
          summary: 'Moisture is the leading influence.',
          top_contributing_features: [],
          feature_importance: {},
        },
        created_at: '2026-07-25T12:00:00Z',
      })
      MockWebSocket.instance.emit('basis_forecast', {
        forecast_id: 'forecast-1',
        transition_id: 'TR-1',
        model_version: 'hgb-test',
        history_window: 20,
        forecast_horizon: 1,
        confidence: 0.9,
        trajectory: [
          {
            step: 1,
            timestamp: '2026-07-25T12:00:10Z',
            basis_weight: 82,
            lower_bound: 81,
            upper_bound: 83,
            deviation_pct: 2.5,
            lower_spec_limit: 78,
            upper_spec_limit: 82,
          },
        ],
        specification: {
          target_basis_weight: 80,
          lower_spec_limit: 78,
          upper_spec_limit: 82,
          current_deviation_pct: 1,
          maximum_predicted_deviation_pct: 2.5,
          crossing_probability: 0.4,
          predicted_crossing_step: 1,
          predicted_crossing_time: '2026-07-25T12:00:10Z',
          remaining_safe_operating_seconds: 10,
          predicted_stabilization_step: null,
        },
        top_influencing_variables: [['stock_flow', 0.6]],
        explanation: 'Stock flow drives the predicted crossing.',
        created_at: '2026-07-25T12:00:00Z',
      })
    })
    expect(screen.getByText('Live stream connected')).toBeInTheDocument()
    expect(screen.getByText('88.4')).toBeInTheDocument()
    expect(screen.getByText('Basis-weight forecast and specification envelope')).toBeInTheDocument()
    expect(screen.getByText('Active Transition: Kraft → CopyPaper')).toBeInTheDocument()
  })
})
