import { afterEach, describe, expect, it, vi } from 'vitest'

import { api } from './client'

describe('API transient failure resilience', () => {
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('retries a transient 502 with exponential backoff', async () => {
    vi.useFakeTimers()
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ error: { message: 'Bad gateway' } }), { status: 502 }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ error: { message: 'Bad gateway' } }), { status: 502 }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            model_type: 'RandomForestRegressor',
            model_version: 'rf-test',
            trained_at: '2026-07-27T00:00:00Z',
            training_records: 20_000,
            feature_count: 10,
            target_metrics: {},
            dataset_checksum: 'checksum',
            supported_outputs: [],
            artifact_path: 'model.joblib',
          }),
          { status: 200 },
        ),
      )
    vi.stubGlobal('fetch', fetchMock)

    const result = api.modelInfo()
    await vi.runAllTimersAsync()

    await expect(result).resolves.toMatchObject({ model_version: 'rf-test' })
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })
})
