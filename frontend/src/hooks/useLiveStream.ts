import { useEffect, useRef, useState } from 'react'

import { api, websocketUrl } from '../api/client'
import type {
  Alert,
  Drift,
  LiveMetrics,
  Prediction,
  ProcessInput,
  Recommendation,
  StreamStatus,
  Forecast,
} from '../api/types'

export interface TrendPoint {
  time: string
  quality: number
  risk: number
  stabilization: number
  steamPressure: number
  moisture: number
  temperature: number
  machineSpeed: number
}

export function useLiveStream() {
  const [connected, setConnected] = useState(false)
  const [live, setLive] = useState<LiveMetrics>({
    sensor: null,
    prediction: null,
    recommendations: [],
    alerts: [],
    drift: null,
    updated_at: null,
  })
  const [status, setStatus] = useState<StreamStatus>()
  const [trends, setTrends] = useState<TrendPoint[]>([])
  const [forecast, setForecast] = useState<Forecast>()
  const reconnect = useRef<number | undefined>(undefined)
  const sensor = useRef<ProcessInput | null>(null)

  useEffect(() => {
    let active = true
    let socket: WebSocket | undefined
    const hydrate = async () => {
      const [metrics, stream] = await Promise.allSettled([api.liveMetrics(), api.streamStatus()])
      if (active) {
        if (metrics.status === 'fulfilled') {
          setLive(metrics.value)
          sensor.current = metrics.value.sensor
        }
        if (stream.status === 'fulfilled') setStatus(stream.value)
      }
    }
    void hydrate().catch(() => undefined)

    const connect = () => {
      socket = new WebSocket(websocketUrl())
      socket.onopen = () => setConnected(true)
      socket.onclose = () => {
        setConnected(false)
        if (active) reconnect.current = window.setTimeout(connect, 2000)
      }
      socket.onmessage = (message) => {
        const event = JSON.parse(message.data) as { event: string; data: unknown }
        if (event.event === 'sensor_update') {
          sensor.current = event.data as ProcessInput
          setLive((current) => ({ ...current, sensor: sensor.current }))
        } else if (event.event === 'prediction') {
          const prediction = event.data as Prediction
          setLive((current) => ({
            ...current,
            prediction,
            updated_at: prediction.created_at,
          }))
          if (sensor.current) {
            const point: TrendPoint = {
              time: new Date(prediction.created_at).toLocaleTimeString(),
              quality: prediction.quality_score,
              risk: prediction.off_spec_probability * 100,
              stabilization: prediction.expected_stabilization_time,
              steamPressure: sensor.current.steam_pressure,
              moisture: sensor.current.moisture,
              temperature: sensor.current.dryer_temperature,
              machineSpeed: sensor.current.machine_speed,
            }
            setTrends((current) => [...current.slice(-29), point])
          }
        } else if (event.event === 'recommendation') {
          setLive((current) => ({
            ...current,
            recommendations: (event.data as { recommendations: Recommendation[] }).recommendations,
          }))
        } else if (event.event === 'alert') {
          setLive((current) => ({
            ...current,
            alerts: [event.data as Alert, ...current.alerts].slice(0, 20),
          }))
        } else if (event.event === 'drift') {
          setLive((current) => ({ ...current, drift: event.data as Drift }))
        } else if (event.event === 'system_status') {
          setStatus(event.data as StreamStatus)
        } else if (event.event === 'basis_forecast') {
          setForecast(event.data as Forecast)
        }
      }
    }
    connect()
    return () => {
      active = false
      if (reconnect.current) window.clearTimeout(reconnect.current)
      socket?.close()
    }
  }, [])

  return { connected, live, status, trends, forecast, setLive }
}
