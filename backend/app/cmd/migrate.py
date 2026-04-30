import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from peewee import BooleanField, CharField, DateTimeField, Model
from playhouse.migrate import PostgresqlMigrator, migrate

from app.models.base.base_model import db
from app.models.user.user_model import User


USER_TABLE_NAME = "user"
MIGRATION_TABLE_NAME = "schema_migrations"


def utc_now() -> datetime:
	return datetime.now(timezone.utc)


class SchemaMigration(Model):
	name = CharField(unique=True, max_length=255)
	applied_at = DateTimeField(default=utc_now)

	class Meta:
		database = db
		table_name = MIGRATION_TABLE_NAME


@dataclass(frozen=True)
class MigrationDefinition:
	name: str
	description: str
	is_satisfied: Callable[[], bool]
	apply: Callable[[PostgresqlMigrator], None]


EXPECTED_USER_COLUMNS = {
	"id",
	"email",
	"password_hash",
	"is_active",
	"is_superuser",
	"created_at",
	"updated_at",
}
PLAYHOUSE_MANAGED_USER_COLUMNS = {
	"is_active",
	"is_superuser",
	"created_at",
	"updated_at",
}


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description="Check and apply backend database migrations")
	subparsers = parser.add_subparsers(dest="command")
	subparsers.add_parser("check", help="Check whether any migrations are pending")
	subparsers.add_parser("apply", help="Apply all pending migrations")
	subparsers.add_parser("ensure", help="Check for pending migrations and apply them if needed")
	parser.set_defaults(command="ensure")
	return parser


def migration_table_exists() -> bool:
	return MIGRATION_TABLE_NAME in db.get_tables()


def user_table_exists() -> bool:
	return USER_TABLE_NAME in db.get_tables()


def get_user_columns() -> set[str]:
	if not user_table_exists():
		return set()
	return {column.name for column in db.get_columns(USER_TABLE_NAME)}


def initial_user_schema_is_satisfied() -> bool:
	return EXPECTED_USER_COLUMNS.issubset(get_user_columns())


def ensure_migration_table() -> None:
	db.create_tables([SchemaMigration], safe=True)


def get_applied_migration_names() -> set[str]:
	if not migration_table_exists():
		return set()
	return {migration.name for migration in SchemaMigration.select(SchemaMigration.name)}


def record_applied_migration(name: str) -> None:
	ensure_migration_table()
	SchemaMigration.get_or_create(name=name)


def apply_initial_user_schema(migrator: PostgresqlMigrator) -> None:
	if not user_table_exists():
		User.create_table(safe=True)
		return

	columns = get_user_columns()
	missing_columns = EXPECTED_USER_COLUMNS - columns
	unsupported_columns = missing_columns - PLAYHOUSE_MANAGED_USER_COLUMNS
	if unsupported_columns:
		raise RuntimeError(
			"Unsupported automatic migration for existing 'user' table. "
			f"Missing columns require manual intervention: {sorted(unsupported_columns)}"
		)

	boolean_operations = []
	if "is_active" in missing_columns:
		boolean_operations.append(migrator.add_column(USER_TABLE_NAME, "is_active", BooleanField(default=True)))
	if "is_superuser" in missing_columns:
		boolean_operations.append(migrator.add_column(USER_TABLE_NAME, "is_superuser", BooleanField(default=False)))
	if boolean_operations:
		with db.atomic():
			migrate(*boolean_operations)

	quoted_user_table = f'"{USER_TABLE_NAME}"'
	if "created_at" in missing_columns:
		with db.atomic():
			migrate(migrator.add_column(USER_TABLE_NAME, "created_at", DateTimeField(null=True)))
			db.execute_sql(f"UPDATE {quoted_user_table} SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
			migrate(migrator.add_not_null(USER_TABLE_NAME, "created_at"))

	if "updated_at" in missing_columns:
		with db.atomic():
			migrate(migrator.add_column(USER_TABLE_NAME, "updated_at", DateTimeField(null=True)))
			db.execute_sql(f"UPDATE {quoted_user_table} SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
			migrate(migrator.add_not_null(USER_TABLE_NAME, "updated_at"))

	if not initial_user_schema_is_satisfied():
		raise RuntimeError("Initial user schema migration did not complete successfully")


def get_migrations() -> list[MigrationDefinition]:
	return [
		MigrationDefinition(
			name="0001_initial_user_schema",
			description="Ensure the user table and required columns exist",
			is_satisfied=initial_user_schema_is_satisfied,
			apply=apply_initial_user_schema,
		),
	]


def get_pending_migrations() -> list[MigrationDefinition]:
	applied_migrations = get_applied_migration_names()
	return [
		migration
		for migration in get_migrations()
		if migration.name not in applied_migrations or not migration.is_satisfied()
	]


def apply_pending_migrations() -> bool:
	pending_migrations = get_pending_migrations()
	if not pending_migrations:
		print("Database schema is up to date.")
		return False

	migrator = PostgresqlMigrator(db)
	for migration_definition in pending_migrations:
		if migration_definition.is_satisfied():
			print(f"Migration {migration_definition.name} already satisfied. Recording state.")
		else:
			print(f"Applying migration {migration_definition.name}: {migration_definition.description}")
			migration_definition.apply(migrator)

		record_applied_migration(migration_definition.name)

	print(f"Applied {len(pending_migrations)} migration(s).")
	return True


def ensure_migrations_applied() -> bool:
	pending_migrations = get_pending_migrations()
	if not pending_migrations:
		print("No pending migrations detected.")
		return False

	print("Pending migrations detected:")
	for migration_definition in pending_migrations:
		print(f" - {migration_definition.name}: {migration_definition.description}")

	return apply_pending_migrations()


def main() -> int:
	parser = build_parser()
	args = parser.parse_args()

	try:
		db.connect(reuse_if_open=True)

		if args.command == "check":
			pending_migrations = get_pending_migrations()
			if pending_migrations:
				print("Pending migrations detected:")
				for migration_definition in pending_migrations:
					print(f" - {migration_definition.name}: {migration_definition.description}")
				return 1
			print("No pending migrations detected.")
			return 0

		if args.command == "apply":
			apply_pending_migrations()
			return 0

		ensure_migrations_applied()
		return 0
	finally:
		if not db.is_closed():
			db.close()


if __name__ == "__main__":
	raise SystemExit(main())