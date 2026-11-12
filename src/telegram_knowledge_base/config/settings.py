from pathlib import Path


class Settings:
    data_dir: Path
    database_path: Path
    collection_limit: int
    page_size: int


def load_settings() -> Settings:
    raise NotImplementedError("MVP-01 configuration is not implemented")
