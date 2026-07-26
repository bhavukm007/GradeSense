import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { api } from '../api/client'
import { ProcessForm } from '../components/process/ProcessForm'
import { PredictionResult } from '../components/prediction/PredictionResult'
import { PageHeader } from '../components/ui/PageHeader'
import { Panel } from '../components/ui/Panel'
import { ErrorState } from '../components/ui/QueryState'
import { useProcessStore } from '../stores/processStore'

export function PredictionPage() {
  const { values, setValues, setBaseline } = useProcessStore()
  const [resultVisible, setResultVisible] = useState(false)
  const queryClient = useQueryClient()
  const prediction = useMutation({
    mutationFn: api.predict,
    onSuccess: (_, submitted) => {
      setBaseline(submitted)
      setResultVisible(true)
      void queryClient.invalidateQueries({ queryKey: ['prediction-history'] })
    },
  })
  return (
    <>
      <PageHeader
        eyebrow="Operator workflow"
        title="Prediction center"
        description="Enter the current transition conditions to score quality, off-spec risk, and stabilization time with the active model."
      />
      <Panel className="mt-8" title="Process conditions">
        <ProcessForm
          values={values}
          onChange={setValues}
          busy={prediction.isPending}
          submitLabel="Run transition prediction"
          onSubmit={(event) => {
            event.preventDefault()
            prediction.mutate(values)
          }}
        />
      </Panel>
      {prediction.error && (
        <div className="mt-5">
          <ErrorState
            message={prediction.error.message}
            onRetry={() => prediction.mutate(values)}
          />
        </div>
      )}
      {prediction.data && resultVisible && (
        <div className="mt-5">
          <PredictionResult prediction={prediction.data} />
        </div>
      )}
    </>
  )
}
