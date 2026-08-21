/* ============================================================================
   AIHarvest PM -- add machines.admin_email   (T-SQL, run from SSMS)

   WHY THIS IS A SCRIPT AND NOT AUTOMATIC
     There is no Alembic in this project, and the one piece of automatic schema
     handling -- Base.metadata.create_all(), gated behind DB_AUTO_CREATE_TABLES
     -- only adds *missing tables*. It never alters a table that already
     exists, so a new column on `machines` will never appear on its own.
     Production deployments run with DB_AUTO_CREATE_TABLES=False anyway. See
     DEPLOY_RUNBOOK.md, "Schema changes".

   WHAT IT DOES
     Adds a nullable admin_email column to `machines`. That is the recipient of
     the work order approval notice; the supplier address stays in
     supplier_email and is used for the completion notice and by the n8n
     daily-pm-checker workflow.

   SAFE TO RE-RUN. The column is only added if it is not already there, and
   nothing is dropped, altered or deleted. Existing rows get NULL, which the
   application treats as "no admin configured" -- approving such a machine's
   work order still succeeds, and the response reports
   notification_status = "skipped".

   USAGE
     Open in SSMS, select the target database in the toolbar, and Execute (F5).
     Then populate the column, e.g.

         UPDATE machines SET admin_email = 'maintenance-admin@example.com'
         WHERE admin_email IS NULL;
   ============================================================================ */

SET NOCOUNT ON;

IF COL_LENGTH('machines', 'admin_email') IS NULL
BEGIN
    ALTER TABLE machines ADD admin_email NVARCHAR(200) NULL;
    PRINT 'Added machines.admin_email.';
END
ELSE
BEGIN
    PRINT 'machines.admin_email already exists -- nothing to do.';
END
GO

/* Verification: both should return a row. */
SELECT
    column_name  = c.name,
    type_name    = t.name,
    max_length   = c.max_length,
    is_nullable  = c.is_nullable
FROM sys.columns c
JOIN sys.types   t ON t.user_type_id = c.user_type_id
WHERE c.object_id = OBJECT_ID('machines')
  AND c.name IN ('supplier_email', 'admin_email')
ORDER BY c.column_id;
GO
