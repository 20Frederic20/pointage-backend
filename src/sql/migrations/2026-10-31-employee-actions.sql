-- Employee actions: edit, (de)activation, transfers, several companies.
-- Idempotent: safe to run more than once. Applies to EXISTING databases;
-- new databases get the same columns from src/sql/read_model.sql and
-- src/sql/event_store.sql.

-- ===== READ database (pointage_read_db, port 7434) =====

-- employees: the company (root directory) of each record.
ALTER TABLE employees ADD COLUMN IF NOT EXISTS company_directory_id character varying(32);

-- employee_assignments: an assignment replaced by a same-day transfer.
ALTER TABLE employee_assignments ADD COLUMN IF NOT EXISTS cancelled boolean DEFAULT false NOT NULL;
