import argparse
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from peewee import BooleanField, CharField, DateTimeField, Model
from psycopg.types.json import Jsonb
from playhouse.migrate import PostgresqlMigrator, migrate

from app.models.base.base_model import db
from app.models.dataset.dataset_model import Dataset, DatasetVersion
from app.models.document.document_model import Document, DocumentChunk
from app.models.evidence.evidence_model import ContradictionWarning, EvidenceItem
from app.models.feature.feature_model import FeatureAnnotation
from app.models.job.job_model import ProcessingJob
from app.models.model.model_config_model import ModelConfig
from app.models.project.project_model import ResearchProject
from app.models.report.report_model import Report
from app.models.run.run_model import AnalysisRun, AnalysisStep, CandidateMatch, CardiacApplicationQuery
from app.models.user.user_model import User
from app.models.sample.sample_model import Sample, Measurement
from app.models.preprocessing.preprocessing_run_model import PreprocessingRun


USER_TABLE_NAME = "user"
MIGRATION_TABLE_NAME = "schema_migrations"
PROJECT_TABLE_NAME = "research_project"
DATASET_TABLE_NAME = "dataset"
DATASET_VERSION_TABLE_NAME = "dataset_version"
DOCUMENT_TABLE_NAME = "document"
DOCUMENT_CHUNK_TABLE_NAME = "document_chunk"
ANALYSIS_RUN_TABLE_NAME = "analysis_run"
CARDIAC_APPLICATION_QUERY_TABLE_NAME = "cardiac_application_query"
ANALYSIS_STEP_TABLE_NAME = "analysis_step"
CANDIDATE_MATCH_TABLE_NAME = "candidate_match"
EVIDENCE_ITEM_TABLE_NAME = "evidence_item"
CONTRADICTION_WARNING_TABLE_NAME = "contradiction_warning"
REPORT_TABLE_NAME = "report"
PROCESSING_JOB_TABLE_NAME = "processing_job"
PREPROCESSING_RUN_TABLE_NAME = "preprocessing_run"
FEATURE_ANNOTATION_TABLE_NAME = "feature_annotation"
MODEL_CONFIG_TABLE_NAME = "model_config"


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
EXPECTED_PROJECT_COLUMNS = {
	"id",
	"name",
	"description",
	"created_at",
	"updated_at",
}
EXPECTED_DATASET_COLUMNS = {
	"id",
	"project_id",
	"name",
	"type",
	"original_filename",
	"storage_path",
	"metadata",
	"created_at",
	"updated_at",
}
EXPECTED_DATASET_VERSION_COLUMNS = {
	"id",
	"dataset_id",
	"version_number",
	"status",
	"storage_path",
	"preprocessing_config",
	"created_at",
}
EXPECTED_DOCUMENT_COLUMNS = {
	"id",
	"project_id",
	"title",
	"original_filename",
	"storage_path",
	"status",
	"metadata",
	"created_at",
	"updated_at",
}
EXPECTED_DOCUMENT_CHUNK_COLUMNS = {
	"id",
	"document_id",
	"chunk_index",
	"page_number",
	"text",
	"vector_id",
	"metadata",
	"created_at",
}
EXPECTED_ANALYSIS_RUN_COLUMNS = {
	"id",
	"project_id",
	"application_query_id",
	"status",
	"selected_config",
	"started_at",
	"finished_at",
	"error_message",
	"created_at",
	"updated_at",
}
EXPECTED_CARDIAC_APPLICATION_QUERY_COLUMNS = {
	"id",
	"project_id",
	"query_text",
	"target_application",
	"target_tissue",
	"function_target",
	"constraints",
	"created_at",
	"updated_at",
}
EXPECTED_ANALYSIS_STEP_COLUMNS = {
	"id",
	"analysis_run_id",
	"sequence_number",
	"step_name",
	"status",
	"input_snapshot",
	"output_snapshot",
	"started_at",
	"finished_at",
	"error_message",
	"created_at",
}
EXPECTED_CANDIDATE_MATCH_COLUMNS = {
	"id",
	"analysis_run_id",
	"dataset_version_id",
	"rank",
	"candidate_name",
	"target_name",
	"score",
	"method",
	"features_used",
	"metadata",
	"created_at",
}
EXPECTED_EVIDENCE_ITEM_COLUMNS = {
	"id",
	"analysis_run_id",
	"candidate_match_id",
	"candidate_name",
	"claim",
	"document_id",
	"document_chunk_id",
	"support_label",
	"score",
	"metadata",
	"created_at",
}
EXPECTED_CONTRADICTION_WARNING_COLUMNS = {
	"id",
	"analysis_run_id",
	"candidate_match_id",
	"candidate_name",
	"warning_type",
	"severity",
	"message",
	"metadata",
	"created_at",
}
EXPECTED_REPORT_COLUMNS = {
	"id",
	"analysis_run_id",
	"status",
	"json_body",
	"markdown_body",
	"storage_path",
	"created_at",
	"updated_at",
}
EXPECTED_PROCESSING_JOB_COLUMNS = {
	"id",
	"job_type",
	"status",
	"payload",
	"attempts",
	"last_error",
	"created_at",
	"updated_at",
	"started_at",
	"finished_at",
}
EXPECTED_SAMPLE_COLUMNS = {
    "id",
    "dataset_version_id",
    "name",
    "type",
    "metadata",
    "created_at",
}
EXPECTED_MEASUREMENT_COLUMNS = {
    "id",
    "sample_id",
    "feature_name",
    "raw_value",
    "normalized_value",
    "unit",
    "created_at",
}
EXPECTED_PREPROCESSING_RUN_COLUMNS = {
	"id",
	"dataset_version_id",
	"status",
	"config",
	"log_path",
	"error_message",
	"started_at",
	"finished_at",
	"created_at",
	"updated_at",
}
EXPECTED_FEATURE_ANNOTATION_COLUMNS = {
    "id",
    "dataset_version_id",
    "feature_name",
    "uniprot",
    "matrisome_division",
    "matrisome_category",
    "location",
    "present_in_heart",
    "created_at",
}
EXPECTED_MODEL_CONFIG_COLUMNS = {
    "id",
    "name",
    "provider",
    "model_id",
    "api_key",
    "is_active",
    "status",
    "metadata_",
    "created_at",
    "updated_at",
}
PROJECT_DATASET_TABLE_EXPECTATIONS = {
	PROJECT_TABLE_NAME: EXPECTED_PROJECT_COLUMNS,
	DATASET_TABLE_NAME: EXPECTED_DATASET_COLUMNS,
	DATASET_VERSION_TABLE_NAME: EXPECTED_DATASET_VERSION_COLUMNS,
}
WORKFLOW_TABLE_EXPECTATIONS = {
	DOCUMENT_TABLE_NAME: EXPECTED_DOCUMENT_COLUMNS,
	DOCUMENT_CHUNK_TABLE_NAME: EXPECTED_DOCUMENT_CHUNK_COLUMNS,
	CARDIAC_APPLICATION_QUERY_TABLE_NAME: EXPECTED_CARDIAC_APPLICATION_QUERY_COLUMNS,
	ANALYSIS_RUN_TABLE_NAME: EXPECTED_ANALYSIS_RUN_COLUMNS,
	ANALYSIS_STEP_TABLE_NAME: EXPECTED_ANALYSIS_STEP_COLUMNS,
	CANDIDATE_MATCH_TABLE_NAME: EXPECTED_CANDIDATE_MATCH_COLUMNS,
	EVIDENCE_ITEM_TABLE_NAME: EXPECTED_EVIDENCE_ITEM_COLUMNS,
	CONTRADICTION_WARNING_TABLE_NAME: EXPECTED_CONTRADICTION_WARNING_COLUMNS,
	REPORT_TABLE_NAME: EXPECTED_REPORT_COLUMNS,
	PROCESSING_JOB_TABLE_NAME: EXPECTED_PROCESSING_JOB_COLUMNS,
}
PLAYHOUSE_MANAGED_USER_COLUMNS = {
	"is_active",
	"is_superuser",
	"created_at",
	"updated_at",
}
SAMPLE_MEASUREMENT_TABLE_EXPECTATIONS = {
    "sample": EXPECTED_SAMPLE_COLUMNS,
    "measurement": EXPECTED_MEASUREMENT_COLUMNS,
}
PREPROCESSING_RUN_TABLE_EXPECTATIONS = {
	PREPROCESSING_RUN_TABLE_NAME: EXPECTED_PREPROCESSING_RUN_COLUMNS,
}
FEATURE_ANNOTATION_TABLE_EXPECTATIONS = {
    FEATURE_ANNOTATION_TABLE_NAME: EXPECTED_FEATURE_ANNOTATION_COLUMNS,
}
MODEL_CONFIG_TABLE_EXPECTATIONS = {
    MODEL_CONFIG_TABLE_NAME: EXPECTED_MODEL_CONFIG_COLUMNS,
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


def table_exists(table_name: str) -> bool:
	return table_name in db.get_tables()


def get_user_columns() -> set[str]:
	if not user_table_exists():
		return set()
	return {column.name for column in db.get_columns(USER_TABLE_NAME)}


def get_table_columns(table_name: str) -> set[str]:
	if not table_exists(table_name):
		return set()
	return {column.name for column in db.get_columns(table_name)}


def get_missing_table_columns(table_expectations: dict[str, set[str]]) -> dict[str, list[str]]:
	missing_columns_by_table: dict[str, list[str]] = {}
	for table_name, expected_columns in table_expectations.items():
		missing_columns = sorted(expected_columns - get_table_columns(table_name))
		if missing_columns:
			missing_columns_by_table[table_name] = missing_columns
	return missing_columns_by_table


def initial_user_schema_is_satisfied() -> bool:
	return EXPECTED_USER_COLUMNS.issubset(get_user_columns())


def tables_schema_is_satisfied(table_expectations: dict[str, set[str]]) -> bool:
	return not get_missing_table_columns(table_expectations)


def raise_partial_schema_error(schema_name: str, table_expectations: dict[str, set[str]]) -> None:
	missing_columns_by_table = get_missing_table_columns(table_expectations)
	if not missing_columns_by_table:
		return

	missing_details = "; ".join(
		f"{table_name} -> {', '.join(columns)}"
		for table_name, columns in missing_columns_by_table.items()
	)
	raise RuntimeError(
		f"{schema_name} schema migration could not repair an existing partial schema automatically. "
		f"Missing columns by table: {missing_details}. "
		"Add the missing columns manually or implement an explicit column migration."
	)


def project_dataset_schema_is_satisfied() -> bool:
	return tables_schema_is_satisfied(PROJECT_DATASET_TABLE_EXPECTATIONS)


def workflow_schema_is_satisfied() -> bool:
	return tables_schema_is_satisfied(WORKFLOW_TABLE_EXPECTATIONS)

def sample_measurement_schema_is_satisfied() -> bool:
    return tables_schema_is_satisfied(SAMPLE_MEASUREMENT_TABLE_EXPECTATIONS)

def preprocessing_run_schema_is_satisfied() -> bool:
	return tables_schema_is_satisfied(PREPROCESSING_RUN_TABLE_EXPECTATIONS)


def feature_annotation_schema_is_satisfied() -> bool:
    return tables_schema_is_satisfied(FEATURE_ANNOTATION_TABLE_EXPECTATIONS)


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


def apply_project_dataset_schema(_migrator: PostgresqlMigrator) -> None:
	db.create_tables([ResearchProject, Dataset, DatasetVersion], safe=True)

	raise_partial_schema_error("Project and dataset", PROJECT_DATASET_TABLE_EXPECTATIONS)


def apply_workflow_schema(_migrator: PostgresqlMigrator) -> None:
	db.create_tables(
		[
			Document,
			DocumentChunk,
			CardiacApplicationQuery,
			AnalysisRun,
			AnalysisStep,
			CandidateMatch,
			EvidenceItem,
			ContradictionWarning,
			Report,
			ProcessingJob,
		],
		safe=True,
	)
	ensure_analysis_run_query_columns()

	raise_partial_schema_error("Workflow", WORKFLOW_TABLE_EXPECTATIONS)


def ensure_analysis_run_query_columns() -> None:
	if not table_exists(ANALYSIS_RUN_TABLE_NAME):
		return

	columns = get_table_columns(ANALYSIS_RUN_TABLE_NAME)
	if "selected_config" not in columns:
		db.execute_sql(f'ALTER TABLE "{ANALYSIS_RUN_TABLE_NAME}" ADD COLUMN selected_config JSONB')

	if "application_query_id" not in columns:
		db.execute_sql(f'ALTER TABLE "{ANALYSIS_RUN_TABLE_NAME}" ADD COLUMN application_query_id UUID')

	columns = get_table_columns(ANALYSIS_RUN_TABLE_NAME)
	legacy_columns = {"query", "target_application", "target_tissue", "constraints"}
	if legacy_columns.issubset(columns):
		backfill_application_queries()

	null_count = db.execute_sql(
		f'SELECT COUNT(*) FROM "{ANALYSIS_RUN_TABLE_NAME}" WHERE application_query_id IS NULL'
	).fetchone()[0]
	if null_count == 0:
		db.execute_sql(f'ALTER TABLE "{ANALYSIS_RUN_TABLE_NAME}" ALTER COLUMN application_query_id SET NOT NULL')
		add_application_query_fk_constraint()


def backfill_application_queries() -> None:
	rows = db.execute_sql(
		f'''
		SELECT id, project_id, query, target_application, target_tissue, constraints, created_at, updated_at
		FROM "{ANALYSIS_RUN_TABLE_NAME}"
		WHERE application_query_id IS NULL
		'''
	).fetchall()

	for row in rows:
		query_id = uuid.uuid4()
		db.execute_sql(
			f'''
			INSERT INTO "{CARDIAC_APPLICATION_QUERY_TABLE_NAME}"
				(id, project_id, query_text, target_application, target_tissue, constraints, created_at, updated_at)
			VALUES (%s, %s, %s, %s, %s, %s, COALESCE(%s, CURRENT_TIMESTAMP), COALESCE(%s, CURRENT_TIMESTAMP))
			''',
			(
				query_id,
				row[1],
				row[2],
				row[3],
				row[4],
				Jsonb(row[5]) if row[5] is not None else None,
				row[6],
				row[7],
			),
		)
		db.execute_sql(
			f'UPDATE "{ANALYSIS_RUN_TABLE_NAME}" SET application_query_id = %s WHERE id = %s',
			(query_id, row[0]),
		)


def add_application_query_fk_constraint() -> None:
	constraint_name = "analysis_run_application_query_id_fkey"
	exists = db.execute_sql(
		"""
		SELECT 1
		FROM pg_constraint
		WHERE conname = %s
		""",
		(constraint_name,),
	).fetchone()
	if exists:
		return

	db.execute_sql(
		f'''
		ALTER TABLE "{ANALYSIS_RUN_TABLE_NAME}"
		ADD CONSTRAINT {constraint_name}
		FOREIGN KEY (application_query_id)
		REFERENCES "{CARDIAC_APPLICATION_QUERY_TABLE_NAME}" (id)
		ON DELETE CASCADE
		'''
	)

def apply_sample_measurement_schema(_migrator: PostgresqlMigrator) -> None:
    db.create_tables([Sample, Measurement], safe=True)
    raise_partial_schema_error("Sample and measurement", SAMPLE_MEASUREMENT_TABLE_EXPECTATIONS)

def apply_preprocessing_run_schema(_migrator: PostgresqlMigrator) -> None:
	db.create_tables([PreprocessingRun], safe=True)
	if table_exists(PREPROCESSING_RUN_TABLE_NAME) and "finished_at" not in get_table_columns(PREPROCESSING_RUN_TABLE_NAME):
		db.execute_sql(f'ALTER TABLE "{PREPROCESSING_RUN_TABLE_NAME}" ADD COLUMN finished_at TIMESTAMP WITH TIME ZONE')
	raise_partial_schema_error("Preprocessing run", PREPROCESSING_RUN_TABLE_EXPECTATIONS)


def apply_feature_annotation_schema(_migrator: PostgresqlMigrator) -> None:
    db.create_tables([FeatureAnnotation], safe=True)
    raise_partial_schema_error("Feature annotation", FEATURE_ANNOTATION_TABLE_EXPECTATIONS)


def model_config_schema_is_satisfied() -> bool:
    return tables_schema_is_satisfied(MODEL_CONFIG_TABLE_EXPECTATIONS)


def apply_model_config_schema(_migrator: PostgresqlMigrator) -> None:
    db.create_tables([ModelConfig], safe=True)
    if table_exists(MODEL_CONFIG_TABLE_NAME) and "status" not in get_table_columns(MODEL_CONFIG_TABLE_NAME):
        db.execute_sql(f'ALTER TABLE "{MODEL_CONFIG_TABLE_NAME}" ADD COLUMN status VARCHAR(50) DEFAULT \'ready\'')
    if table_exists(MODEL_CONFIG_TABLE_NAME) and "api_key_encrypted" in get_table_columns(MODEL_CONFIG_TABLE_NAME) and "api_key" not in get_table_columns(MODEL_CONFIG_TABLE_NAME):
        db.execute_sql(f'ALTER TABLE "{MODEL_CONFIG_TABLE_NAME}" RENAME COLUMN api_key_encrypted TO api_key')
    raise_partial_schema_error("Model config", MODEL_CONFIG_TABLE_EXPECTATIONS)


def get_migrations() -> list[MigrationDefinition]:
	return [
		MigrationDefinition(
			name="0001_initial_user_schema",
			description="Ensure the user table and required columns exist",
			is_satisfied=initial_user_schema_is_satisfied,
			apply=apply_initial_user_schema,
		),
		MigrationDefinition(
			name="0002_project_dataset_schema",
			description="Ensure project, dataset, and dataset version tables exist",
			is_satisfied=project_dataset_schema_is_satisfied,
			apply=apply_project_dataset_schema,
		),
		MigrationDefinition(
			name="0003_workflow_schema",
			description="Ensure document, run, evidence, warning, report, and job tables exist",
			is_satisfied=workflow_schema_is_satisfied,
			apply=apply_workflow_schema,
		),
		MigrationDefinition(
            name="0004_sample_measurement_schema",
            description="Create sample and measurement tables for parsed biological data",
            is_satisfied=sample_measurement_schema_is_satisfied,
            apply=apply_sample_measurement_schema,
        ),
		MigrationDefinition(
			name="0005_preprocessing_run_schema",
			description="Create preprocessing_run table for tracking data preparation jobs",
			is_satisfied=preprocessing_run_schema_is_satisfied,
			apply=apply_preprocessing_run_schema,
		),
		MigrationDefinition(
			name="0006_feature_annotation_schema",
			description="Create feature_annotation table for per-protein matrisome/heart annotation",
			is_satisfied=feature_annotation_schema_is_satisfied,
			apply=apply_feature_annotation_schema,
		),
		MigrationDefinition(
			name="0007_model_config_schema",
			description="Create model_config table for LLM model management",
			is_satisfied=model_config_schema_is_satisfied,
			apply=apply_model_config_schema,
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
