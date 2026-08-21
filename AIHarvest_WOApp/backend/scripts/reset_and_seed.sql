/* ============================================================================
   AIHarvest PM -- reset and reseed the demo database   (T-SQL, run from SSMS)

   The SQL equivalent of running both Python seed scripts back to back:

       python scripts/seed_data.py          -> machines + maintenance_history
       python scripts/seed_work_orders.py   -> ai_decisions + work_orders

   WHAT IT DOES
     1. DELETES every row from maintenance_history, work_orders, ai_decisions
        and machines. Optionally workflow_logs too -- see @ClearWorkflowLogs.
     2. Reseeds 75 machines, their maintenance history, and 45 work orders
        spread across every lifecycle status.
     3. Prints a verification summary, including the dashboard's pm_status
        breakdown, so you can see the reset landed.

   WHAT IT DOES NOT DO
     - It does not CREATE, ALTER or DROP anything. The tables must already
       exist. Schema creation still comes from `python scripts/init_db.py`, or
       from starting the backend with DB_AUTO_CREATE_TABLES=True. Keeping DDL
       out of here is deliberate: this script cannot drift from the SQLAlchemy
       models if it never declares them.

   DESTRUCTIVE. Every row in those four tables is deleted. It all runs in one
   transaction, so a mid-run failure rolls the whole thing back -- but a
   successful run is not undoable. Do not point it at a database holding
   anything you care about.

   USAGE
     Open in SSMS, confirm @ExpectedDatabase matches the database you mean to
     reset, select that database in the toolbar, and Execute (F5).
   ============================================================================ */

SET NOCOUNT ON;
SET XACT_ABORT ON;

/* ---------------------------------------------------------------------------
   Guard: refuse to run anywhere unexpected.

   The realistic accident is not a mistyped script, it is the right script in
   the wrong query window. Edit this one line if your database has another
   name.
   --------------------------------------------------------------------------- */
DECLARE @ExpectedDatabase SYSNAME = N'aiharvest_pm';
/* RAISERROR's %s substitution takes a variable, not a function call. */
DECLARE @ActualDatabase SYSNAME = DB_NAME();

IF @ActualDatabase <> @ExpectedDatabase
BEGIN
    RAISERROR (
        'Refusing to run: connected to database [%s] but this script expects [%s]. Select the right database, or edit @ExpectedDatabase.',
        16, 1, @ActualDatabase, @ExpectedDatabase);
    SET NOEXEC ON;
END
GO

/* Every table must be present before we delete anything. */
DECLARE @missing NVARCHAR(500) = N'';

SELECT @missing = @missing + CASE WHEN OBJECT_ID(t.n) IS NULL THEN t.n + N' ' ELSE N'' END
FROM (VALUES (N'machines'), (N'maintenance_history'), (N'work_orders'),
             (N'ai_decisions'), (N'workflow_logs')) AS t(n);

IF LEN(@missing) > 0
BEGIN
    RAISERROR (
        'Missing table(s): %s -- run `python scripts/init_db.py` first. This script seeds data only, it does not create schema.',
        16, 1, @missing);
    SET NOEXEC ON;
END
GO

/* ============================================================================
   Knobs
   ============================================================================ */

/* Set to 1 to also clear workflow_logs (the n8n run history). The Python seed
   scripts leave that table alone, so this defaults to 0. */
DECLARE @ClearWorkflowLogs BIT = 0;

DECLARE @MachineCount INT = 75;

/* Machine PM distribution. These are the numbers seed_data.py actually
   produces: int(75*0.20) = 15 and int(75*0.33) = 24, leaving 36. (README.md's
   table says 25/35 -- the code rounds down, and the code is what runs.) */
DECLARE @OverdueCount INT = 15;
DECLARE @DueSoonCount INT = 24;
/* The OK count is whatever is left over. */

/* Leave this many of the most-overdue machines WITHOUT any work order.

   0 reproduces the Python exactly, and is the default for that reason. Be
   aware of what it costs you: open work orders are handed out overdue-first,
   there are 27 of them and only 15 overdue machines, so every overdue machine
   ends up with one. The dashboard then shows Overdue = 0, and a live demo of
   "AI raises a work order" has no machine to act on -- the create endpoint
   refuses a second open order with HTTP 409.

   Set this to 5 or so to hold a few genuinely-overdue machines in reserve. The
   verification output at the bottom reports the count either way. */
DECLARE @ReserveOverdueWithoutWo INT = 0;

/* Keep these matching the backend .env, or the seeded AI decisions will not
   agree with how the running app classifies them. */
DECLARE @Window    INT           = 30;    -- PM_DUE_DAYS
DECLARE @Threshold DECIMAL(3, 2) = 0.70;  -- CONFIDENCE_THRESHOLD

DECLARE @Today DATE     = CAST(GETDATE() AS DATE);
DECLARE @Now   DATETIME = GETDATE();
DECLARE @Year  INT      = YEAR(GETDATE());

/* ============================================================================
   Reference data -- the constants from the top of the two Python scripts
   ============================================================================ */

IF OBJECT_ID('tempdb..#Nums')        IS NOT NULL DROP TABLE #Nums;
IF OBJECT_ID('tempdb..#Suppliers')   IS NOT NULL DROP TABLE #Suppliers;
IF OBJECT_ID('tempdb..#Frequencies') IS NOT NULL DROP TABLE #Frequencies;
IF OBJECT_ID('tempdb..#Locations')   IS NOT NULL DROP TABLE #Locations;
IF OBJECT_ID('tempdb..#Types')       IS NOT NULL DROP TABLE #Types;
IF OBJECT_ID('tempdb..#MaintTypes')  IS NOT NULL DROP TABLE #MaintTypes;
IF OBJECT_ID('tempdb..#MaintNotes')  IS NOT NULL DROP TABLE #MaintNotes;
IF OBJECT_ID('tempdb..#Explain')     IS NOT NULL DROP TABLE #Explain;
IF OBJECT_ID('tempdb..#Approvers')   IS NOT NULL DROP TABLE #Approvers;
IF OBJECT_ID('tempdb..#DoneNotes')   IS NOT NULL DROP TABLE #DoneNotes;
IF OBJECT_ID('tempdb..#CancelNotes') IS NOT NULL DROP TABLE #CancelNotes;

/* A numbers table, used to fan single rows out into many. */
CREATE TABLE #Nums (i INT PRIMARY KEY);
INSERT #Nums (i)
SELECT TOP (1000) ROW_NUMBER() OVER (ORDER BY (SELECT NULL))
FROM sys.all_objects a CROSS JOIN sys.all_objects b;

CREATE TABLE #Suppliers (name VARCHAR(200), email VARCHAR(200));
INSERT #Suppliers (name, email) VALUES
    ('TechServ Inc',     'natalia4nib@gmail.com'),
    ('MainCo Solutions', 'natalia4nib@gmail.com'),
    ('FixIt Pro',        'natalia4nib@gmail.com'),
    ('Industrial Care',  'natalia4nib@gmail.com'),
    ('MachineGuard',     'natalia4nib@gmail.com'),
    ('ProMaintain',      'natalia4nib@gmail.com'),
    ('QuickFix Ltd',     'natalia4nib@gmail.com'),
    ('ReliaTech',        'natalia4nib@gmail.com'),
    ('ServiceMax',       'natalia4nib@gmail.com'),
    ('EliteMaint',       'natalia4nib@gmail.com');

/* days = the interval WorkOrderService._calculate_next_pm_date uses. */
CREATE TABLE #Frequencies (name VARCHAR(20), days INT);
INSERT #Frequencies (name, days) VALUES ('Monthly', 30), ('Bimonthly', 60), ('Yearly', 365);

CREATE TABLE #Locations (name VARCHAR(200));
INSERT #Locations (name) VALUES ('Zone A'), ('Zone B'), ('Zone C'), ('Zone D'), ('Zone E');

CREATE TABLE #Types (name VARCHAR(100));
INSERT #Types (name) VALUES
    ('CNC Mill'), ('Lathe'), ('Press'), ('Grinder'), ('Welder'), ('Conveyor'),
    ('Robot Arm'), ('Drill Press'), ('Band Saw'), ('Plasma Cutter'),
    ('Assembly Line'), ('Packaging Machine');

CREATE TABLE #MaintTypes (name VARCHAR(50));
INSERT #MaintTypes (name) VALUES ('Preventive'), ('Corrective'), ('Inspection');

CREATE TABLE #MaintNotes (note VARCHAR(500));
INSERT #MaintNotes (note) VALUES
    ('Regular maintenance performed. All systems operational.'),
    ('Routine inspection completed. No issues found.'),
    ('Preventive maintenance completed successfully.'),
    ('Parts lubricated and checked. Running smoothly.'),
    ('Comprehensive service performed. Machine in good condition.'),
    ('Scheduled maintenance completed. Performance optimal.'),
    ('Inspection and minor adjustments completed.');

/* AI explanation templates, per PM bucket. The placeholders are filled in
   below with REPLACE, standing in for Python's str.format. */
CREATE TABLE #Explain (bucket VARCHAR(10), template VARCHAR(1000));
INSERT #Explain (bucket, template) VALUES
    ('overdue',  'Next PM date passed {days} days ago and no open work order exists. The machine runs on a {freq} cycle, so the window is already a full interval behind. Raising a work order at High priority.'),
    ('overdue',  'PM is {days} days overdue on a {freq} schedule. The last three history entries were all routine preventive visits with no faults logged, so this is a lapsed schedule rather than a developing issue.'),
    ('overdue',  'Overdue by {days} days. {supplier} handled the previous service on this asset and holds the {freq} contract, so assigning back to them keeps the service record continuous.'),
    ('due_soon', 'Next PM falls in {days} days, inside the {window}-day planning window. Scheduling now gives {supplier} lead time to confirm before the date arrives.'),
    ('due_soon', 'PM due in {days} days on a {freq} cycle. History shows the previous visit closed cleanly, so a standard preventive scope is enough.'),
    ('due_soon', 'Due in {days} days. Raising early at Medium priority so the visit can be batched with the other {location} assets falling due the same week.'),
    ('ok',       'Next PM is {days} days out, beyond the {window}-day window, but the last visit logged a corrective repair. Raising a follow-up inspection at Low priority to confirm the fix held.'),
    ('ok',       'Not yet due -- {days} days remain. Raising a Low priority order against a maintenance note from the previous {freq} visit.');

CREATE TABLE #Approvers (email VARCHAR(200));
INSERT #Approvers (email) VALUES
    ('m.reyes@innoark.com'), ('s.tan@innoark.com'),
    ('j.okafor@innoark.com'), ('planning@innoark.com');

CREATE TABLE #DoneNotes (note VARCHAR(500));
INSERT #DoneNotes (note) VALUES
    ('PM completed. Filters and belts replaced, no faults found.'),
    ('PM completed. Lubrication and alignment checked, within tolerance.'),
    ('PM completed. Worn seal replaced during the visit; asset returned to service the same day.'),
    ('PM completed. All checks passed, next cycle confirmed with the supplier.');

CREATE TABLE #CancelNotes (note VARCHAR(500));
INSERT #CancelNotes (note) VALUES
    ('Cancelled -- machine was taken offline for a line reconfiguration before the visit; PM will be re-raised once it is back in service.'),
    ('Cancelled -- duplicate of an order already raised for the same PM window.'),
    ('Cancelled -- supplier could not meet the window and the schedule was moved to the next cycle.'),
    ('Cancelled -- PM was completed during an unrelated corrective visit, so the scheduled work is no longer needed.');

/* ============================================================================
   Work order plan -- STATUS_PLAN from seed_work_orders.py
   ============================================================================ */

IF OBJECT_ID('tempdb..#Plan') IS NOT NULL DROP TABLE #Plan;
CREATE TABLE #Plan (
    seq     INT IDENTITY(1, 1) PRIMARY KEY,  -- drives WO-YYYY-NNNN
    status  VARCHAR(30) NOT NULL,
    is_open BIT         NOT NULL
);

/* Inserted in STATUS_PLAN order, so wo_number is assigned in the same sequence
   the Python loop produces.

   The last column is the count. Draft is 0 on purpose: nothing in the running
   application ever creates a Draft work order. ai_service.py passes
   status="Pending_Approval", and so does the n8n Create Work Order node. The
   only Draft default is the one on WorkOrderCreate, which neither caller
   exercises. seed_work_orders.py invents 6 Drafts anyway, producing demo rows
   in a state the system itself cannot reach -- so those 6 are folded into
   Pending_Approval here. Set Draft back to 6 and Pending_Approval to 9 for
   exact Python parity.

   This does not change how the AI treats them. The system prompt in
   llm_providers/base.py says "WAIT: If ANY work order has status
   Pending_Approval or Draft", so both block a new order identically. */
INSERT #Plan (status, is_open)
SELECT p.status, p.is_open
FROM (VALUES
        ('Draft',            1, 1,  0),
        ('Pending_Approval', 1, 2, 15),
        ('Approved',         1, 3, 12),
        ('Completed',        0, 4, 14),
        ('Cancelled',        0, 5,  4)
     ) AS p(status, is_open, ord, cnt)
JOIN #Nums n ON n.i <= p.cnt
ORDER BY p.ord, n.i;

/* ============================================================================
   Clear, then reseed -- one transaction
   ============================================================================ */

/* Counted into variables first: PRINT takes only a scalar expression, and a
   subquery inline here is a compile error that takes the whole batch with it. */
DECLARE @beforeMachines   INT = (SELECT COUNT(*) FROM machines);
DECLARE @beforeWorkOrders INT = (SELECT COUNT(*) FROM work_orders);

PRINT '--- Before ---';
PRINT '  machines:    ' + CAST(@beforeMachines   AS VARCHAR(10));
PRINT '  work_orders: ' + CAST(@beforeWorkOrders AS VARCHAR(10));

BEGIN TRY
    BEGIN TRANSACTION;

    /* Order matters. maintenance_history points at work_orders and work_orders
       points at ai_decisions, both with NO ACTION rather than a cascade, so
       children go before parents or the delete is refused. */
    DELETE FROM maintenance_history;
    DELETE FROM work_orders;
    DELETE FROM ai_decisions;
    DELETE FROM machines;

    IF @ClearWorkflowLogs = 1
        DELETE FROM workflow_logs;

    /* Restart the identity counters so a reset looks like a fresh install --
       MACH-001 is row id 1 again. RESEED 0 makes the next insert 1. */
    DBCC CHECKIDENT ('machines',            RESEED, 0) WITH NO_INFOMSGS;
    DBCC CHECKIDENT ('maintenance_history', RESEED, 0) WITH NO_INFOMSGS;
    DBCC CHECKIDENT ('work_orders',         RESEED, 0) WITH NO_INFOMSGS;
    DBCC CHECKIDENT ('ai_decisions',        RESEED, 0) WITH NO_INFOMSGS;
    IF @ClearWorkflowLogs = 1
        DBCC CHECKIDENT ('workflow_logs',   RESEED, 0) WITH NO_INFOMSGS;

    /* ========================================================================
       1. Machines
       ======================================================================== */

    INSERT machines (machine_id, name, description, location, pm_frequency,
                     last_pm_date, next_pm_date, assigned_supplier,
                     supplier_email, status, created_at, updated_at)
    SELECT
        'MACH-' + RIGHT('000' + CAST(n.i AS VARCHAR(10)), 3),
        t.name + ' ' + CAST(n.i AS VARCHAR(10)),
        'Production machine in ' + loc.name,
        loc.name,
        f.name,
        DATEADD(DAY, -f.days, d.next_pm),
        d.next_pm,
        s.name,
        s.email,
        'Active',
        @Now,
        @Now
    FROM #Nums n
    CROSS APPLY (SELECT TOP 1 name, days FROM #Frequencies ORDER BY NEWID()) f
    CROSS APPLY (SELECT TOP 1 name       FROM #Locations   ORDER BY NEWID()) loc
    CROSS APPLY (SELECT TOP 1 name       FROM #Types       ORDER BY NEWID()) t
    CROSS APPLY (SELECT TOP 1 name, email FROM #Suppliers  ORDER BY NEWID()) s
    CROSS APPLY (
        /* Buckets in the order the Python builds them, so MACH-001..015 are
           the overdue ones. Ranges: overdue 1-60 days past, due soon 1-30 days
           out, ok 31-365 days out. */
        SELECT next_pm = CASE
            WHEN n.i <= @OverdueCount
                THEN DATEADD(DAY, -(1 + ABS(CHECKSUM(NEWID())) % 60), @Today)
            WHEN n.i <= @OverdueCount + @DueSoonCount
                THEN DATEADD(DAY,  (1 + ABS(CHECKSUM(NEWID())) % 30), @Today)
            ELSE DATEADD(DAY, (31 + ABS(CHECKSUM(NEWID())) % 335), @Today)
        END
    ) d
    WHERE n.i <= @MachineCount;

    /* Note: seed_data.py draws a second, independent random location for the
       description, so its text can contradict the location column. Here they
       are the same value -- the only deliberate difference from the Python. */

    /* ========================================================================
       2. Maintenance history -- 3 to 8 records per machine, 30 to 730 days old
       ======================================================================== */

    IF OBJECT_ID('tempdb..#HistPlan') IS NOT NULL DROP TABLE #HistPlan;
    CREATE TABLE #HistPlan (machine_id INT PRIMARY KEY, cnt INT);

    /* The per-machine count is drawn once, here, rather than inline: TOP (n)
       will not accept a non-deterministic expression like NEWID(). */
    INSERT #HistPlan (machine_id, cnt)
    SELECT id, 3 + ABS(CHECKSUM(NEWID())) % 6 FROM machines;

    INSERT maintenance_history (machine_id, maintenance_date, maintenance_type,
                                notes, performed_by, work_order_id, created_at)
    SELECT
        h.machine_id,
        DATEADD(DAY, -(30 + ABS(CHECKSUM(NEWID())) % 701), @Today),
        mt.name,
        nt.note,
        s.name,
        NULL,
        @Now
    FROM #HistPlan h
    JOIN #Nums n ON n.i <= h.cnt
    CROSS APPLY (SELECT TOP 1 name FROM #MaintTypes ORDER BY NEWID()) mt
    CROSS APPLY (SELECT TOP 1 note FROM #MaintNotes ORDER BY NEWID()) nt
    CROSS APPLY (SELECT TOP 1 name FROM #Suppliers  ORDER BY NEWID()) s;

    /* ========================================================================
       3. Work orders, and the AI decisions behind them

       Built in two passes. Every value is drawn up front into #Wo, so each
       random choice is made exactly once and stays stable across the inserts
       that follow. Then ai_decisions is inserted and its generated ids are
       captured, so the work orders can point at them.
       ======================================================================== */

    IF OBJECT_ID('tempdb..#Wo') IS NOT NULL DROP TABLE #Wo;
    CREATE TABLE #Wo (
        seq            INT PRIMARY KEY,
        status         VARCHAR(30)   NOT NULL,
        is_open        BIT           NOT NULL,
        machine_id     INT           NOT NULL,
        bucket         VARCHAR(10)   NOT NULL,
        days_until     INT           NOT NULL,
        priority       VARCHAR(20)   NOT NULL,
        from_ai        BIT           NOT NULL,
        created_at     DATETIME      NOT NULL,
        updated_at     DATETIME      NOT NULL,
        confidence     DECIMAL(3, 2) NOT NULL,
        explanation    VARCHAR(1000) NOT NULL,
        notes          VARCHAR(2000) NULL,
        scheduled_date DATE          NULL,
        completed_date DATE          NULL,
        approved_at    DATETIME      NULL,
        approved_by    VARCHAR(200)  NULL,
        notified       BIT           NOT NULL,
        notified_at    DATETIME      NULL,
        input_context  VARCHAR(MAX)  NULL,
        raw_response   VARCHAR(MAX)  NULL
    );

    /* Machine assignment, matching the Python:
         - open orders (Draft / Pending_Approval / Approved) each take a
           distinct machine, drawn overdue-first, which is the order the daily
           PM check would surface them. One open order per machine is the
           invariant WorkOrderService enforces when it refuses a duplicate.
         - closed orders (Completed / Cancelled) may reuse any machine, since
           they are history. */
    IF OBJECT_ID('tempdb..#Assign') IS NOT NULL DROP TABLE #Assign;
    CREATE TABLE #Assign (seq INT PRIMARY KEY, machine_id INT NOT NULL);

    INSERT #Assign (seq, machine_id)
    SELECT p.seq, m.id
    FROM (SELECT seq, ROW_NUMBER() OVER (ORDER BY seq) AS open_rank
          FROM #Plan WHERE is_open = 1) p
    JOIN (SELECT id, ROW_NUMBER() OVER (ORDER BY next_pm_date, id) AS rn
          FROM machines) m
      /* Offsetting the rank skips the N most-overdue machines, leaving them
         with no work order at all -- see @ReserveOverdueWithoutWo. */
      ON m.rn = p.open_rank + @ReserveOverdueWithoutWo;

    INSERT #Assign (seq, machine_id)
    SELECT p.seq, r.id
    FROM #Plan p
    CROSS APPLY (SELECT TOP 1 id FROM machines ORDER BY NEWID()) r
    WHERE p.is_open = 0;

    INSERT #Wo (seq, status, is_open, machine_id, bucket, days_until, priority,
                from_ai, created_at, updated_at, confidence, explanation,
                notified)
    SELECT
        p.seq,
        p.status,
        p.is_open,
        m.id,
        b.bucket,
        b.days_until,
        pr.priority,
        ai.from_ai,
        c.created_at,
        /* Overwritten per status below; a bare created_at is the
           Draft / Pending_Approval case, which nothing has happened to yet. */
        c.created_at,
        conf.confidence,
        /* str.format, spelled out */
        REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(ex.template,
            '{days}',     CAST(ABS(b.days_until) AS VARCHAR(10))),
            '{freq}',     LOWER(m.pm_frequency)),
            '{supplier}', ISNULL(m.assigned_supplier, 'the supplier')),
            '{location}', ISNULL(m.location, 'the plant')),
            '{window}',   CAST(@Window AS VARCHAR(10))),
        0
    FROM #Plan p
    JOIN #Assign a  ON a.seq = p.seq
    JOIN machines m ON m.id = a.machine_id
    CROSS APPLY (
        SELECT days_until = DATEDIFF(DAY, @Today, m.next_pm_date),
               bucket = CASE
                   WHEN DATEDIFF(DAY, @Today, m.next_pm_date) < 0        THEN 'overdue'
                   WHEN DATEDIFF(DAY, @Today, m.next_pm_date) <= @Window THEN 'due_soon'
                   ELSE 'ok' END
    ) b
    CROSS APPLY (
        /* Priority follows urgency, with the occasional bump a planner would
           make -- the weightings from _priority_for(). */
        SELECT priority = CASE b.bucket
            WHEN 'overdue'  THEN CASE WHEN ABS(CHECKSUM(NEWID())) % 100 < 85 THEN 'High' ELSE 'Medium' END
            WHEN 'due_soon' THEN CASE WHEN ABS(CHECKSUM(NEWID())) % 100 < 70 THEN 'Medium'
                                      WHEN ABS(CHECKSUM(NEWID())) % 100 < 50 THEN 'High'
                                      ELSE 'Low' END
            ELSE                 CASE WHEN ABS(CHECKSUM(NEWID())) % 100 < 80 THEN 'Low' ELSE 'Medium' END
        END
    ) pr
    /* 70% of orders come from the AI path, the rest are planner-raised. */
    CROSS APPLY (SELECT from_ai = CASE WHEN ABS(CHECKSUM(NEWID())) % 100 < 70 THEN 1 ELSE 0 END) ai
    CROSS APPLY (
        /* Age the records so the list is not one flat timestamp. Closed orders
           reach further back than open ones. */
        SELECT created_at = DATEADD(HOUR, -(ABS(CHECKSUM(NEWID())) % 24),
            DATEADD(DAY, -CASE WHEN p.is_open = 0
                               THEN 20 + ABS(CHECKSUM(NEWID())) % 71
                               ELSE      ABS(CHECKSUM(NEWID())) % 15 END, @Now))
    ) c
    CROSS APPLY (
        /* Overdue cases are the clear-cut ones, so they score highest. The
           'ok' band straddles the threshold on purpose, to exercise the
           review path. */
        SELECT confidence = CASE b.bucket
            WHEN 'overdue'  THEN 0.88 + (ABS(CHECKSUM(NEWID())) % 10) / 100.0
            WHEN 'due_soon' THEN 0.72 + (ABS(CHECKSUM(NEWID())) % 20) / 100.0
            ELSE                 0.58 + (ABS(CHECKSUM(NEWID())) % 19) / 100.0
        END
    ) conf
    CROSS APPLY (SELECT TOP 1 template FROM #Explain e
                 WHERE e.bucket = b.bucket ORDER BY NEWID()) ex;

    /* Notes: the AI path quotes its own explanation, the manual path reads the
       way a planner would write it. */
    UPDATE w
    SET notes = CASE WHEN w.from_ai = 1
                     THEN 'AI-generated work order. ' + w.explanation
                     ELSE 'Raised by planning against the ' + LOWER(m.pm_frequency)
                          + ' PM schedule for ' + m.name
                          + ' (' + ISNULL(m.location, 'unknown') + ').'
                END
    FROM #Wo w JOIN machines m ON m.id = w.machine_id;

    /* --- Approved: approved, notified, and given a date ------------------- */
    UPDATE #Wo
    SET approved_at = DATEADD(DAY, ABS(CHECKSUM(NEWID())) % 4, created_at),
        notified    = 1,
        /* Half sit in the past, so the Complete action is reachable in the UI. */
        scheduled_date = CASE WHEN ABS(CHECKSUM(NEWID())) % 100 < 50
                              THEN DATEADD(DAY, -(1 + ABS(CHECKSUM(NEWID())) % 10), @Today)
                              ELSE DATEADD(DAY,  (2 + ABS(CHECKSUM(NEWID())) % 20), @Today)
                         END
    WHERE status = 'Approved';

    UPDATE #Wo SET notified_at = approved_at, updated_at = approved_at
    WHERE status = 'Approved';

    UPDATE w SET approved_by = a.email
    FROM #Wo w CROSS APPLY (SELECT TOP 1 email FROM #Approvers ORDER BY NEWID()) a
    WHERE w.status = 'Approved';

    /* --- Completed: approved, scheduled, then done ------------------------ */
    UPDATE #Wo
    SET approved_at    = DATEADD(DAY, ABS(CHECKSUM(NEWID())) % 3, created_at),
        scheduled_date = CAST(DATEADD(DAY, 3 + ABS(CHECKSUM(NEWID())) % 10, created_at) AS DATE),
        notified       = 1
    WHERE status = 'Completed';

    /* completed_date trails scheduled_date by 0-3 days, never past today.
       Drawn in its own pass because it reads the scheduled_date set above. */
    UPDATE #Wo
    SET completed_date = CASE
            WHEN DATEADD(DAY, ABS(CHECKSUM(NEWID())) % 4, scheduled_date) > @Today
            THEN @Today
            ELSE DATEADD(DAY, ABS(CHECKSUM(NEWID())) % 4, scheduled_date)
        END
    WHERE status = 'Completed';

    UPDATE #Wo
    SET notified_at = approved_at,
        updated_at  = CAST(completed_date AS DATETIME)
    WHERE status = 'Completed';

    UPDATE w SET approved_by = a.email
    FROM #Wo w CROSS APPLY (SELECT TOP 1 email FROM #Approvers ORDER BY NEWID()) a
    WHERE w.status = 'Completed';

    UPDATE w SET notes = w.notes + ' ' + d.note
    FROM #Wo w CROSS APPLY (SELECT TOP 1 note FROM #DoneNotes ORDER BY NEWID()) d
    WHERE w.status = 'Completed';

    /* --- Cancelled: never scheduled, closed out with a reason ------------- */
    UPDATE #Wo
    SET updated_at = DATEADD(DAY, 1 + ABS(CHECKSUM(NEWID())) % 8, created_at)
    WHERE status = 'Cancelled';

    UPDATE w SET notes = w.notes + ' ' + c.note
    FROM #Wo w CROSS APPLY (SELECT TOP 1 note FROM #CancelNotes ORDER BY NEWID()) c
    WHERE w.status = 'Cancelled';

    /* --- The JSON audit payloads ----------------------------------------- */
    UPDATE w
    SET input_context =
            '{' + CHAR(13) + CHAR(10) +
            '  "machine": {' + CHAR(13) + CHAR(10) +
            '    "machine_id": "'        + STRING_ESCAPE(m.machine_id, 'json') + '",' + CHAR(13) + CHAR(10) +
            '    "name": "'             + STRING_ESCAPE(m.name, 'json') + '",' + CHAR(13) + CHAR(10) +
            '    "location": "'          + STRING_ESCAPE(ISNULL(m.location, ''), 'json') + '",' + CHAR(13) + CHAR(10) +
            '    "pm_frequency": "'      + STRING_ESCAPE(m.pm_frequency, 'json') + '",' + CHAR(13) + CHAR(10) +
            '    "last_pm_date": '       + CASE WHEN m.last_pm_date IS NULL THEN 'null'
                                                ELSE '"' + CONVERT(VARCHAR(10), m.last_pm_date, 23) + '"' END + ',' + CHAR(13) + CHAR(10) +
            '    "next_pm_date": "'      + CONVERT(VARCHAR(10), m.next_pm_date, 23) + '",' + CHAR(13) + CHAR(10) +
            '    "assigned_supplier": "' + STRING_ESCAPE(ISNULL(m.assigned_supplier, ''), 'json') + '",' + CHAR(13) + CHAR(10) +
            '    "days_until_pm": '      + CAST(w.days_until AS VARCHAR(10)) + CHAR(13) + CHAR(10) +
            '  },' + CHAR(13) + CHAR(10) +
            '  "maintenance_history": "' + CAST(hc.n AS VARCHAR(10)) + ' prior records reviewed",' + CHAR(13) + CHAR(10) +
            '  "existing_work_orders": [],' + CHAR(13) + CHAR(10) +
            '  "decision_timestamp": "'  + CONVERT(VARCHAR(23), w.created_at, 126) + '"' + CHAR(13) + CHAR(10) +
            '}',
        raw_response =
            '{' + CHAR(13) + CHAR(10) +
            '  "decision": "CREATE_WORK_ORDER",' + CHAR(13) + CHAR(10) +
            '  "priority": "'    + w.priority + '",' + CHAR(13) + CHAR(10) +
            '  "confidence": '   + CONVERT(VARCHAR(10), w.confidence) + ',' + CHAR(13) + CHAR(10) +
            '  "explanation": "' + STRING_ESCAPE(w.explanation, 'json') + '"' + CHAR(13) + CHAR(10) +
            '}'
    FROM #Wo w
    JOIN machines m ON m.id = w.machine_id
    CROSS APPLY (SELECT n = COUNT(*) FROM maintenance_history h
                 WHERE h.machine_id = w.machine_id) hc
    WHERE w.from_ai = 1;

    /* --- ai_decisions, capturing the generated ids ------------------------
       MERGE rather than INSERT because only MERGE's OUTPUT clause can emit a
       source column (seq) alongside inserted.id -- which is what lets the work
       orders below find the decision they belong to. */
    IF OBJECT_ID('tempdb..#AiMap') IS NOT NULL DROP TABLE #AiMap;
    CREATE TABLE #AiMap (seq INT PRIMARY KEY, ai_id INT NOT NULL);

    MERGE ai_decisions AS tgt
    USING (SELECT * FROM #Wo WHERE from_ai = 1) AS src
    ON 1 = 0
    WHEN NOT MATCHED THEN
        INSERT (machine_id, decision, priority, confidence, explanation,
                input_context, llm_provider, llm_model, raw_response,
                auto_executed, requires_review, created_at)
        VALUES (src.machine_id, 'CREATE_WORK_ORDER', src.priority, src.confidence,
                src.explanation, src.input_context, 'OpenAI', 'gpt-4',
                src.raw_response,
                CASE WHEN src.confidence >= @Threshold THEN 1 ELSE 0 END,
                CASE WHEN src.confidence <  @Threshold THEN 1 ELSE 0 END,
                src.created_at)
    OUTPUT src.seq, inserted.id INTO #AiMap (seq, ai_id);

    /* --- work_orders ------------------------------------------------------ */
    INSERT work_orders (wo_number, machine_id, status, priority, creation_source,
                        ai_decision_id, scheduled_date, completed_date, notes,
                        notification_sent, notification_sent_at, created_at,
                        updated_at, approved_at, approved_by)
    SELECT
        'WO-' + CAST(@Year AS VARCHAR(4)) + '-' + RIGHT('0000' + CAST(w.seq AS VARCHAR(10)), 4),
        w.machine_id,
        w.status,
        w.priority,
        CASE WHEN w.from_ai = 1 THEN 'AI' ELSE 'Manual' END,
        map.ai_id,
        w.scheduled_date,
        w.completed_date,
        w.notes,
        w.notified,
        w.notified_at,
        w.created_at,
        w.updated_at,
        w.approved_at,
        w.approved_by
    FROM #Wo w
    LEFT JOIN #AiMap map ON map.seq = w.seq;

    COMMIT TRANSACTION;
    PRINT 'Committed.';
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    PRINT '--- ROLLED BACK: nothing was changed ---';
    THROW;
END CATCH
GO

/* ============================================================================
   Verification
   ============================================================================ */

SELECT 'machines' AS [table], COUNT(*) AS [rows] FROM machines
UNION ALL SELECT 'maintenance_history', COUNT(*) FROM maintenance_history
UNION ALL SELECT 'work_orders',         COUNT(*) FROM work_orders
UNION ALL SELECT 'ai_decisions',        COUNT(*) FROM ai_decisions
UNION ALL SELECT 'workflow_logs',       COUNT(*) FROM workflow_logs;

SELECT status,
       COUNT(*)                                                  AS work_orders,
       SUM(CASE WHEN creation_source = 'AI' THEN 1 ELSE 0 END)    AS from_ai,
       SUM(CASE WHEN scheduled_date IS NOT NULL THEN 1 ELSE 0 END) AS with_date
FROM work_orders
GROUP BY status
ORDER BY CASE status WHEN 'Draft' THEN 1 WHEN 'Pending_Approval' THEN 2
                     WHEN 'Approved' THEN 3 WHEN 'Completed' THEN 4 ELSE 5 END;

/* The dashboard badge, computed the way MachineService.calculate_pm_status
   does. Use this to confirm the reset produced machines in every state -- in
   particular wo_created, which only appears when an open work order has no
   confirmed date yet. */
SELECT pm_status, COUNT(*) AS machines
FROM (
    SELECT CASE
        WHEN EXISTS (SELECT 1 FROM work_orders w
                     WHERE w.machine_id = m.id
                       AND w.status = 'Approved'
                       AND w.scheduled_date IS NOT NULL)                      THEN 'scheduled'
        WHEN EXISTS (SELECT 1 FROM work_orders w
                     WHERE w.machine_id = m.id
                       AND w.status IN ('Draft', 'Pending_Approval', 'Approved')) THEN 'wo_created'
        WHEN m.next_pm_date <  CAST(GETDATE() AS DATE)                        THEN 'overdue'
        WHEN m.next_pm_date <= DATEADD(DAY, 30, CAST(GETDATE() AS DATE))      THEN 'due_soon'
        ELSE 'ok'
    END AS pm_status
    FROM machines m
) x
GROUP BY pm_status
ORDER BY CASE pm_status WHEN 'overdue' THEN 1 WHEN 'due_soon' THEN 2
                        WHEN 'wo_created' THEN 3 WHEN 'scheduled' THEN 4 ELSE 5 END;

/* How many overdue machines are still free for a live "AI raises a work order"
   demo. Zero is not a failure, but it does mean the create endpoint will answer
   409 for every overdue machine -- raise @ReserveOverdueWithoutWo if you need
   targets. */
SELECT COUNT(*) AS [overdue machines with no open WO]
FROM machines m
WHERE m.next_pm_date < CAST(GETDATE() AS DATE)
  AND NOT EXISTS (SELECT 1 FROM work_orders w
                  WHERE w.machine_id = m.id
                    AND w.status IN ('Draft', 'Pending_Approval', 'Approved'));

/* Every column should read OK. */
SELECT
    CASE WHEN NOT EXISTS (
        SELECT machine_id FROM work_orders
        WHERE status IN ('Draft', 'Pending_Approval', 'Approved')
        GROUP BY machine_id HAVING COUNT(*) > 1)
    THEN 'OK' ELSE 'FAIL' END AS [one open WO per machine],
    CASE WHEN NOT EXISTS (
        SELECT 1 FROM work_orders
        WHERE (CASE WHEN creation_source = 'AI' THEN 1 ELSE 0 END)
           <> (CASE WHEN ai_decision_id IS NOT NULL THEN 1 ELSE 0 END))
    THEN 'OK' ELSE 'FAIL' END AS [AI orders carry a decision],
    CASE WHEN NOT EXISTS (
        SELECT 1 FROM work_orders WHERE completed_date > CAST(GETDATE() AS DATE))
    THEN 'OK' ELSE 'FAIL' END AS [no future completions],
    CASE WHEN NOT EXISTS (
        SELECT 1 FROM work_orders
        WHERE completed_date IS NOT NULL AND completed_date < scheduled_date)
    THEN 'OK' ELSE 'FAIL' END AS [completed on or after scheduled],
    CASE WHEN NOT EXISTS (
        SELECT 1 FROM machines WHERE next_pm_date IS NULL)
    THEN 'OK' ELSE 'FAIL' END AS [every machine has a next PM date];
GO

SET NOEXEC OFF;
