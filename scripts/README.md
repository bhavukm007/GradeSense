# Project scripts

`generate_and_train.py` regenerates the configured synthetic dataset and trains a versioned model
artifact. Run it after installing the backend package:

```bash
cd backend
alembic upgrade head
python ../scripts/generate_and_train.py
```
# Phase 05 forecasting

`generate_and_train_forecast.py` is the explicit, opt-in pipeline for the sequential dataset and
dedicated Basis Weight forecast artifact. It never overwrites the legacy snapshot dataset or model.
Training examples are grouped by transition before the validation split and windows never cross a
transition boundary.
