from enum import Enum


class DataSource(str, Enum):
    ONCHAIN = "ONCHAIN"
    CEX_API = "CEX_API"
    CSV_IMPORT = "CSV_IMPORT"
    MANUAL = "MANUAL"
