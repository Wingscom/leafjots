from dependency_injector import containers, providers

from cryptotax.config import Settings
from cryptotax.db.session import build_engine, build_session_factory


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(modules=["cryptotax.api.deps"])

    settings = providers.Singleton(Settings)

    engine = providers.Singleton(
        build_engine,
        database_url=settings.provided.database_url,
        echo=settings.provided.debug,
    )

    session_factory = providers.Singleton(
        build_session_factory,
        engine=engine,
    )
