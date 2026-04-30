import os
from peewee import Model, PostgresqlDatabase

db = PostgresqlDatabase(
    os.getenv("POSTGRES_DB", "postgres"),
    user=os.getenv("POSTGRES_USER", "postgres"),
    password=os.getenv("POSTGRES_PASSWORD", "postgres"),
    host=os.getenv("POSTGRES_HOST", "db"),
    port=int(os.getenv("POSTGRES_PORT", "5432")),
)

class BaseModel(Model):
    class Meta:
        database = db


def ping_db() -> None:
    with db.connection_context():
        db.execute_sql("SELECT 1")
        