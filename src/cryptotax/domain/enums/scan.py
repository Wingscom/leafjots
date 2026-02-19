from enum import Enum


class ScanProvider(str, Enum):
    ETHERSCAN = "ETHERSCAN"
    BLOCKSCOUT = "BLOCKSCOUT"
    ROUTESCAN = "ROUTESCAN"
