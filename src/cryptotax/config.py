from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_host: str = "localhost"
    db_port: int = 54377
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_name: str = "leafjots"
    redis_url: str = "redis://localhost:6379/0"
    alchemy_api_key: str = ""
    etherscan_api_key: str = ""
    coingecko_api_key: str = ""
    cryptocompare_api_key: str = ""
    solana_rpc_url: str = "https://api.mainnet-beta.solana.com"
    helius_api_key: str = ""
    binance_api_key: str = ""
    binance_api_secret: str = ""
    encryption_key: str = "change-me-32-bytes-key-for-ferne"
    secret_key: str = "change-me"
    debug: bool = True
    usd_vnd_rate: int = 25000  # Default USD/VND exchange rate

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    class Config:
        env_file = ".env"


settings = Settings()
