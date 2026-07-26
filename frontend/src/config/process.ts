import type { ProcessInput } from '../api/types'

export const grades = ['Kraft', 'CopyPaper', 'Newsprint', 'Coated', 'Tissue']

export const defaultProcessInput: ProcessInput = {
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

export const numericFields: Array<{
  key: Exclude<keyof ProcessInput, 'current_grade' | 'target_grade'>
  label: string
  unit: string
  min: number
  max: number
  step: number
}> = [
  { key: 'machine_speed', label: 'Machine Speed', unit: 'm/min', min: 350, max: 1200, step: 1 },
  { key: 'steam_pressure', label: 'Steam Pressure', unit: 'bar', min: 3, max: 9.5, step: 0.1 },
  { key: 'dryer_temperature', label: 'Dryer Temperature', unit: '°C', min: 80, max: 145, step: 1 },
  { key: 'moisture', label: 'Moisture', unit: '%', min: 2.5, max: 10, step: 0.1 },
  { key: 'basis_weight', label: 'Basis Weight', unit: 'g/m²', min: 40, max: 220, step: 1 },
  { key: 'caliper', label: 'Caliper', unit: 'µm', min: 45, max: 300, step: 1 },
  { key: 'pulp_consistency', label: 'Pulp Consistency', unit: '%', min: 2.2, max: 5.5, step: 0.1 },
  { key: 'stock_flow', label: 'Stock Flow', unit: 'L/min', min: 1200, max: 5500, step: 10 },
  { key: 'refining_energy', label: 'Refining Energy', unit: 'kWh/t', min: 80, max: 260, step: 1 },
  {
    key: 'headbox_pressure',
    label: 'Headbox Pressure',
    unit: 'bar',
    min: 1.5,
    max: 5.5,
    step: 0.1,
  },
  { key: 'reel_tension', label: 'Reel Tension', unit: 'kN/m', min: 1, max: 6.5, step: 0.1 },
  {
    key: 'ambient_temperature',
    label: 'Ambient Temperature',
    unit: '°C',
    min: 12,
    max: 42,
    step: 1,
  },
  { key: 'humidity', label: 'Humidity', unit: '%', min: 20, max: 95, step: 1 },
]
