from typing import cast

import pytest
from playhouse.migrate import PostgresqlMigrator

from app.cmd import migrate as migration_module


def test_apply_project_dataset_schema_reports_missing_columns(monkeypatch: pytest.MonkeyPatch) -> None:
	columns_by_table = {
		table_name: expected_columns.copy()
		for table_name, expected_columns in migration_module.PROJECT_DATASET_TABLE_EXPECTATIONS.items()
	}
	columns_by_table[migration_module.PROJECT_TABLE_NAME].remove("description")
	columns_by_table[migration_module.DATASET_TABLE_NAME].remove("metadata")

	monkeypatch.setattr(migration_module.db, "create_tables", lambda _models, safe=True: None)
	monkeypatch.setattr(migration_module, "get_table_columns", lambda table_name: columns_by_table.get(table_name, set()))
	migrator = cast(PostgresqlMigrator, object())

	with pytest.raises(RuntimeError) as exc_info:
		migration_module.apply_project_dataset_schema(migrator)

	message = str(exc_info.value)
	assert "Project and dataset schema migration could not repair an existing partial schema automatically." in message
	assert "research_project -> description" in message
	assert "dataset -> metadata" in message
	assert "dataset_version" not in message


def test_apply_workflow_schema_reports_missing_columns(monkeypatch: pytest.MonkeyPatch) -> None:
	columns_by_table = {
		table_name: expected_columns.copy()
		for table_name, expected_columns in migration_module.WORKFLOW_TABLE_EXPECTATIONS.items()
	}
	columns_by_table[migration_module.DOCUMENT_TABLE_NAME].remove("status")
	columns_by_table[migration_module.ANALYSIS_RUN_TABLE_NAME].remove("selected_config")
	columns_by_table[migration_module.CARDIAC_APPLICATION_QUERY_TABLE_NAME].remove("function_target")

	monkeypatch.setattr(migration_module.db, "create_tables", lambda _models, safe=True: None)
	monkeypatch.setattr(migration_module, "ensure_analysis_run_query_columns", lambda: None)
	monkeypatch.setattr(migration_module, "get_table_columns", lambda table_name: columns_by_table.get(table_name, set()))
	migrator = cast(PostgresqlMigrator, object())

	with pytest.raises(RuntimeError) as exc_info:
		migration_module.apply_workflow_schema(migrator)

	message = str(exc_info.value)
	assert "Workflow schema migration could not repair an existing partial schema automatically." in message
	assert "document -> status" in message
	assert "analysis_run -> selected_config" in message
	assert "cardiac_application_query -> function_target" in message
	assert "report ->" not in message
