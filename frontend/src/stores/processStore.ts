import { create } from 'zustand'

import type { ProcessInput } from '../api/types'
import { defaultProcessInput } from '../config/process'

interface ProcessState {
  values: ProcessInput
  baseline?: ProcessInput
  setValues: (values: ProcessInput) => void
  setBaseline: (values: ProcessInput) => void
  reset: () => void
}

export const useProcessStore = create<ProcessState>((set) => ({
  values: defaultProcessInput,
  setValues: (values) => set({ values }),
  setBaseline: (baseline) => set({ baseline }),
  reset: () => set({ values: defaultProcessInput, baseline: undefined }),
}))
