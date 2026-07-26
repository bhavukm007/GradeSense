# GradeSense Frontend

React 19 and TypeScript operator workspace for live transition monitoring, prediction, forecasting,
intervention comparison, recommendation lifecycle, history, model governance, health, metrics,
audit, configuration, and exports.

## Development

```bash
npm ci
npm run dev
```

Set `VITE_API_URL` when the backend is not at `http://localhost:8000`.

## Quality

```bash
npm test -- --run
npm run lint
npm run format
npm run build
```

Routes are lazy-loaded from `src/app/App.tsx`. TanStack Query owns server state, Zustand retains the
operator process workspace/theme, and Recharts renders operational and forecast visualizations.
