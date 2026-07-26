import numpy as np

from app.services.dataset import SyntheticDatasetGenerator


def test_generator_produces_realistic_causal_dataset() -> None:
    frame = SyntheticDatasetGenerator().generate(20_000, seed=17)

    assert len(frame) == 20_000
    assert frame.isna().sum().sum() == 0
    assert frame["off_spec_probability"].between(0, 1).all()
    assert frame["quality_score"].between(0, 100).all()
    assert frame["machine_speed"].between(350, 1_200).all()
    assert frame["current_grade"].nunique() == 5
    assert frame["target_grade"].nunique() == 5
    assert np.isclose(
        frame["off_spec_probability"].corr(frame["quality_score"]),
        -1,
        atol=0.25,
    )
    assert frame["steam_pressure"].corr(frame["dryer_temperature"]) > 0.45


def test_generator_is_reproducible() -> None:
    generator = SyntheticDatasetGenerator()
    first = generator.generate(1000, seed=91)
    second = generator.generate(1000, seed=91)
    assert first.equals(second)
