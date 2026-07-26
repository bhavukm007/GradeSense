"""Generate the Phase 02 dataset and train the active prediction model."""

from app.config.settings import get_settings
from app.database.session import SessionFactory
from app.services.intelligence import IntelligenceService


def main() -> None:
    settings = get_settings()
    with SessionFactory() as session:
        result = IntelligenceService(settings, session).regenerate(
            settings.dataset_records, settings.dataset_seed
        )
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
