import { Clock3, ShieldAlert, Sparkles } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import type { Prediction } from '../../api/types'
import { formatDate, formatNumber, formatPercent, labelize } from '../../lib/format'
import { MetricCard } from '../ui/MetricCard'
import { Panel } from '../ui/Panel'

export function PredictionResult({ prediction }: { prediction: Prediction }) {
  const importance = Object.entries(prediction.explanation.feature_importance)
    .map(([name, value]) => ({ name: labelize(name), value: value * 100 }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 10)
  return (
    <div className="space-y-5" aria-live="polite">
      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard
          icon={Sparkles}
          label="Quality Score"
          value={`${formatNumber(prediction.quality_score)} / 100`}
          tone="emerald"
        />
        <MetricCard
          icon={ShieldAlert}
          label="Off-spec Probability"
          value={formatPercent(prediction.off_spec_probability)}
          tone="rose"
        />
        <MetricCard
          icon={Clock3}
          label="Stabilization Time"
          value={`${formatNumber(prediction.expected_stabilization_time)} min`}
          tone="amber"
        />
      </div>
      <Panel title="Model explanation">
        <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
          {prediction.explanation.summary}
        </p>
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          {prediction.explanation.top_contributing_features.map((feature) => (
            <div key={feature.feature} className="rounded-xl bg-slate-50 p-4 dark:bg-white/[0.04]">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-semibold">{labelize(feature.feature)}</span>
                <span className="text-xs text-slate-500">
                  {formatNumber(feature.importance * 100)}% importance
                </span>
              </div>
              <p className="mt-1 text-xs text-slate-500">
                {String(feature.value)} · {feature.direction} · contribution{' '}
                {formatNumber(feature.contribution, 3)}
              </p>
            </div>
          ))}
        </div>
      </Panel>
      <Panel title="Feature importance">
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={importance} layout="vertical" margin={{ left: 25 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis type="number" unit="%" />
              <YAxis type="category" dataKey="name" width={125} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(value) => `${formatNumber(Number(value))}%`} />
              <Bar dataKey="value" fill="#2dd4bf" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Panel>
      <p className="text-xs text-slate-500">
        Prediction ID: {prediction.prediction_id} · Executed {formatDate(prediction.created_at)} ·
        Model {prediction.model_version}
      </p>
    </div>
  )
}
