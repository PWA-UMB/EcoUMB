from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarativa única; ``Base.metadata`` es la fuente de verdad de Alembic."""
