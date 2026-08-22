import React, { useCallback, useEffect, useMemo, useState } from 'react';

import { Button, Card, CardContent, CardHeader, Input, ThemeToggle } from '../components/ui';
import demoResetService, { describeError, tokenStore } from '../services/demoResetService';

/**
 * Demo reset page.
 *
 * Deliberately outside Layout: it renders with no sidebar and no navigation, so
 * a tab left open during a demo does not look like part of the application.
 * Reached from the copyright line in the sidebar footer, which is as close to
 * unnoticeable as a link gets.
 *
 * The passphrase gate is not decoration -- the endpoint behind this page deletes
 * every row in five tables. See routers/admin.py.
 */

// Form values only. The passphrase lives in sessionStorage, handled by
// tokenStore, so it does not persist past the tab.
const FORM_KEY = 'aiharvest.demoReset.v1';

// key      -- the request field
// apiKey   -- how the database spells the status, which is how the response is
//             keyed. Spelled out rather than derived from the label: deriving it
//             makes the response silently read as 0 the day a label is reworded.
// open     -- occupies a machine of its own
const STATUS_FIELDS = [
  { key: 'draft', apiKey: 'Draft', label: 'Draft', open: true },
  { key: 'pending_approval', apiKey: 'Pending_Approval', label: 'Pending Approval', open: true },
  { key: 'approved', apiKey: 'Approved', label: 'Approved', open: true },
  { key: 'completed', apiKey: 'Completed', label: 'Completed', open: false },
  { key: 'cancelled', apiKey: 'Cancelled', label: 'Cancelled', open: false },
];

const PM_STATUS_LABELS = {
  overdue: 'Overdue',
  due_soon: 'Due soon',
  wo_created: 'WO raised',
  scheduled: 'Scheduled',
  ok: 'OK',
};

const PM_STATUS_ORDER = ['overdue', 'due_soon', 'wo_created', 'scheduled', 'ok'];

const toInt = (value) => {
  const parsed = parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : 0;
};

const loadRememberedForm = () => {
  try {
    const raw = localStorage.getItem(FORM_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

const rememberForm = (form) => {
  try {
    localStorage.setItem(FORM_KEY, JSON.stringify(form));
  } catch {
    /* a browser that refuses storage just means no prefill next time */
  }
};

/** Values are held as strings so a field can be cleared while being retyped. */
const formFromDefaults = (defaults) => ({
  admin_email: defaults.admin_email || '',
  supplier_email: defaults.supplier_email || '',
  machine_count: String(defaults.machine_count ?? 75),
  reserve_overdue_without_wo: String(defaults.reserve_overdue_without_wo ?? 5),
  draft: String(defaults.status_counts?.Draft ?? 0),
  pending_approval: String(defaults.status_counts?.Pending_Approval ?? 15),
  approved: String(defaults.status_counts?.Approved ?? 12),
  completed: String(defaults.status_counts?.Completed ?? 14),
  cancelled: String(defaults.status_counts?.Cancelled ?? 4),
});

const SectionHeading = ({ children, hint }) => (
  <div className="mb-4">
    <h2 className="text-base font-semibold text-content">{children}</h2>
    {hint && <p className="text-sm text-content-muted mt-1">{hint}</p>}
  </div>
);

const CountRow = ({ label, value, emphasis = false }) => (
  <div className="flex items-baseline justify-between py-1.5 border-b border-line last:border-0">
    <span className={emphasis ? 'text-sm font-medium text-content' : 'text-sm text-content-muted'}>
      {label}
    </span>
    <span className={`text-sm font-semibold tabular-nums ${emphasis ? 'text-content' : 'text-content'}`}>
      {value}
    </span>
  </div>
);

const DemoReset = () => {
  const [token, setToken] = useState(() => tokenStore.get());
  const [passphrase, setPassphrase] = useState('');
  const [unlocking, setUnlocking] = useState(false);
  const [unlockError, setUnlockError] = useState('');

  const [defaults, setDefaults] = useState(null);
  const [form, setForm] = useState(null);

  const [confirmText, setConfirmText] = useState('');
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState('');
  const [result, setResult] = useState(null);

  const unlocked = Boolean(token && defaults);

  const field = (key) => (event) => {
    setForm((prev) => ({ ...prev, [key]: event.target.value }));
    setResult(null);
    setRunError('');
  };

  /**
   * A successful defaults call is what proves the passphrase. Remembered form
   * values win over server defaults, but the emails fall back to the server so
   * a changed .env still shows through.
   */
  const unlock = useCallback(async (candidate) => {
    setUnlocking(true);
    setUnlockError('');
    try {
      const data = await demoResetService.getDefaults(candidate);
      const remembered = loadRememberedForm();
      setDefaults(data);
      setForm({ ...formFromDefaults(data), ...(remembered || {}) });
      setToken(candidate);
      tokenStore.set(candidate);
    } catch (error) {
      setUnlockError(describeError(error));
      setToken('');
      tokenStore.clear();
    } finally {
      setUnlocking(false);
    }
  }, []);

  // A token already in sessionStorage means this tab has been here before.
  useEffect(() => {
    const existing = tokenStore.get();
    if (existing) unlock(existing);
  }, [unlock]);

  const machineCount = toInt(form?.machine_count);
  const reserved = toInt(form?.reserve_overdue_without_wo);
  const counts = useMemo(
    () => Object.fromEntries(STATUS_FIELDS.map((f) => [f.key, toInt(form?.[f.key])])),
    [form]
  );

  const openOrders = counts.draft + counts.pending_approval + counts.approved;
  const totalOrders = openOrders + counts.completed + counts.cancelled;
  const availableMachines = machineCount - reserved;

  /**
   * The same constraint the backend enforces, checked here so the operator sees
   * it while typing instead of after submitting. Every open order needs a
   * machine of its own; closed orders are history and may share.
   */
  const budgetError = useMemo(() => {
    if (!form) return '';
    if (machineCount < 1) return 'At least one machine is needed.';
    if (reserved >= machineCount) {
      return `Holding back ${reserved} of ${machineCount} machines leaves none to raise work orders against.`;
    }
    if (openOrders > availableMachines) {
      return `${openOrders} open work orders need one machine each, but only ${availableMachines} of ${machineCount} are available after holding back ${reserved} overdue.`;
    }
    if (!form.admin_email.trim() || !form.supplier_email.trim()) {
      return 'Both email addresses are required.';
    }
    return '';
  }, [form, machineCount, reserved, openOrders, availableMachines]);

  const confirmed = confirmText.trim().toUpperCase() === 'RESET';
  const canRun = unlocked && !budgetError && confirmed && !running;

  const runReset = async () => {
    if (!canRun) return;
    setRunning(true);
    setRunError('');
    setResult(null);

    const payload = {
      admin_email: form.admin_email.trim(),
      supplier_email: form.supplier_email.trim(),
      machine_count: machineCount,
      reserve_overdue_without_wo: reserved,
      ...counts,
    };

    try {
      const data = await demoResetService.runReset(token, payload);
      setResult(data);
      setConfirmText('');
      rememberForm(form);
      // Row counts on screen are now stale -- refresh them from the result.
      setDefaults((prev) => (prev ? {
        ...prev,
        current_row_counts: {
          machines: data.machines,
          maintenance_history: data.maintenance_history,
          work_orders: data.work_orders,
          ai_decisions: data.ai_decisions,
          workflow_logs: data.workflow_logs,
        },
      } : prev));
    } catch (error) {
      setRunError(describeError(error));
    } finally {
      setRunning(false);
    }
  };

  const relock = () => {
    tokenStore.clear();
    setToken('');
    setDefaults(null);
    setForm(null);
    setResult(null);
    setPassphrase('');
    setConfirmText('');
  };

  return (
    <div className="min-h-screen bg-canvas">
      <header className="h-16 bg-raised border-b border-line flex items-center px-4 sm:px-6 shadow-card">
        <span className="material-icons-round text-content-muted text-2xl flex-shrink-0">
          settings_backup_restore
        </span>
        <div className="ml-3 min-w-0">
          <div className="text-[15px] font-semibold leading-tight text-content truncate">
            Demo Database Reset
          </div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.08em] leading-tight text-content-muted">
            Internal utility
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2">
          {unlocked && (
            <Button variant="text" size="sm" startIcon="lock" onClick={relock}>
              Lock
            </Button>
          )}
          <ThemeToggle />
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        <div className="rounded-lg border border-error-line bg-error-soft px-4 py-3 mb-6 flex gap-3">
          <span className="material-icons-round text-error-on-soft text-xl flex-shrink-0">
            warning
          </span>
          <div className="text-sm text-error-on-soft">
            <p className="font-semibold">This deletes the demo database.</p>
            <p className="mt-1">
              Every machine, work order, AI decision, maintenance record and
              workflow log is removed and replaced with a freshly generated set.
              It runs in one transaction, so a failure changes nothing &mdash; but
              a successful run cannot be undone.
            </p>
          </div>
        </div>

        {!unlocked ? (
          <Card>
            <CardHeader>
              <SectionHeading hint="Set as DEMO_RESET_TOKEN in the backend environment.">
                Passphrase
              </SectionHeading>
            </CardHeader>
            <CardContent>
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  if (passphrase.trim()) unlock(passphrase.trim());
                }}
              >
                <Input
                  label="Reset passphrase"
                  type="password"
                  value={passphrase}
                  onChange={(event) => setPassphrase(event.target.value)}
                  placeholder="Enter the demo reset passphrase"
                  startIcon="key"
                  autoFocus
                  error={Boolean(unlockError)}
                  helperText={unlockError || undefined}
                />
                <div className="mt-4 flex items-center gap-3">
                  <Button
                    type="submit"
                    disabled={!passphrase.trim() || unlocking}
                    startIcon={unlocking ? undefined : 'lock_open'}
                  >
                    {unlocking ? 'Checking…' : 'Unlock'}
                  </Button>
                  <a
                    href="/machines"
                    className="text-sm text-primary-on-soft hover:underline"
                  >
                    Back to the app
                  </a>
                </div>
              </form>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <SectionHeading hint="Written to every seeded machine. A reset overwrites whatever is there now.">
                  Notification addresses
                </SectionHeading>
              </CardHeader>
              <CardContent className="space-y-4">
                <Input
                  label="Admin email"
                  type="email"
                  value={form.admin_email}
                  onChange={field('admin_email')}
                  startIcon="admin_panel_settings"
                  required
                  helperText="Receives the notice when a work order is approved."
                />
                <Input
                  label="Supplier email"
                  type="email"
                  value={form.supplier_email}
                  onChange={field('supplier_email')}
                  startIcon="local_shipping"
                  required
                  helperText="Receives the supplier notification, and replies to it feed the date extractor."
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <SectionHeading>Machine estate</SectionHeading>
              </CardHeader>
              <CardContent className="grid gap-4 sm:grid-cols-2">
                <Input
                  label="Machines"
                  type="number"
                  min={1}
                  max={defaults.max_machines}
                  value={form.machine_count}
                  onChange={field('machine_count')}
                  helperText={`1 to ${defaults.max_machines}. 20% land overdue, 33% due soon.`}
                />
                <Input
                  label="Overdue machines held back"
                  type="number"
                  min={0}
                  max={defaults.max_machines}
                  value={form.reserve_overdue_without_wo}
                  onChange={field('reserve_overdue_without_wo')}
                  helperText="Left with no work order, so a live AI demo has a machine to act on."
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <SectionHeading hint="Draft, Pending Approval and Approved are open states: each needs a machine of its own. Completed and Cancelled are history and may share.">
                  Work orders
                </SectionHeading>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 sm:grid-cols-2">
                  {STATUS_FIELDS.map((status) => (
                    <Input
                      key={status.key}
                      label={status.label}
                      type="number"
                      min={0}
                      max={defaults.max_per_status}
                      value={form[status.key]}
                      onChange={field(status.key)}
                      helperText={
                        status.key === 'draft'
                          ? 'Nothing in the running app creates a Draft — 0 is intentional.'
                          : status.open
                            ? 'Open — needs its own machine.'
                            : 'History — may reuse a machine.'
                      }
                    />
                  ))}
                </div>

                <div className="mt-5 rounded-lg bg-sunken px-4 py-3">
                  <CountRow label="Total work orders" value={totalOrders} emphasis />
                  <CountRow
                    label="Open orders (need a machine each)"
                    value={`${openOrders} of ${Math.max(availableMachines, 0)} available`}
                  />
                </div>

                {budgetError && (
                  <p className="mt-3 text-sm text-error-on-soft flex gap-2">
                    <span className="material-icons-round text-base flex-shrink-0">error_outline</span>
                    <span>{budgetError}</span>
                  </p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <SectionHeading hint="Currently in the database, and about to be deleted.">
                  Before
                </SectionHeading>
              </CardHeader>
              <CardContent>
                {Object.entries(defaults.current_row_counts).map(([table, count]) => (
                  <CountRow key={table} label={table.replace(/_/g, ' ')} value={count} />
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardContent className="py-5">
                <Input
                  label='Type RESET to confirm'
                  value={confirmText}
                  onChange={(event) => setConfirmText(event.target.value)}
                  placeholder="RESET"
                  className="max-w-xs"
                />
                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <Button
                    variant="error"
                    onClick={runReset}
                    disabled={!canRun}
                    startIcon={running ? undefined : 'delete_forever'}
                  >
                    {running ? 'Resetting…' : 'Reset database'}
                  </Button>
                  <a
                    href="/machines"
                    className="text-sm text-primary-on-soft hover:underline"
                  >
                    Back to the app
                  </a>
                </div>

                {runError && (
                  <p className="mt-4 text-sm text-error-on-soft flex gap-2">
                    <span className="material-icons-round text-base flex-shrink-0">error_outline</span>
                    <span>{runError}</span>
                  </p>
                )}
              </CardContent>
            </Card>

            {result && (
              <Card className="border-success-line">
                <CardHeader className="border-success-line bg-success-soft">
                  <div className="flex items-center gap-2">
                    <span className="material-icons-round text-success-on-soft">
                      check_circle
                    </span>
                    <h2 className="text-base font-semibold text-success-on-soft">
                      Reset complete in {result.elapsed_seconds}s
                    </h2>
                  </div>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div>
                    <h3 className="text-sm font-semibold text-content mb-2">Rows created</h3>
                    <CountRow label="machines" value={result.machines} />
                    <CountRow label="maintenance history" value={result.maintenance_history} />
                    <CountRow label="work orders" value={result.work_orders} />
                    <CountRow label="ai decisions" value={result.ai_decisions} />
                    <CountRow
                      label="workflow logs"
                      value={result.workflow_logs_cleared ? 'cleared' : result.workflow_logs}
                    />
                  </div>

                  <div>
                    <h3 className="text-sm font-semibold text-content mb-2">
                      Work orders by status
                    </h3>
                    {STATUS_FIELDS.map((status) => (
                      <CountRow
                        key={status.key}
                        label={status.label}
                        value={result.work_orders_by_status[status.apiKey] ?? 0}
                      />
                    ))}
                  </div>

                  <div>
                    <h3 className="text-sm font-semibold text-content mb-2">
                      Dashboard PM status
                    </h3>
                    {PM_STATUS_ORDER.filter(
                      (key) => result.machines_by_pm_status[key] !== undefined
                    ).map((key) => (
                      <CountRow
                        key={key}
                        label={PM_STATUS_LABELS[key]}
                        value={result.machines_by_pm_status[key]}
                      />
                    ))}
                  </div>

                  {/* The number that decides whether a live "AI raises a work
                      order" demo has anywhere to go. At zero the create
                      endpoint answers 409 for every overdue machine. */}
                  <div
                    className={`rounded-lg px-4 py-3 text-sm ${
                      result.overdue_machines_without_open_wo > 0
                        ? 'bg-success-soft text-success-on-soft'
                        : 'bg-warning-soft text-warning-on-soft'
                    }`}
                  >
                    {result.overdue_machines_without_open_wo > 0 ? (
                      <>
                        <strong>{result.overdue_machines_without_open_wo}</strong> overdue
                        {' '}machine{result.overdue_machines_without_open_wo === 1 ? '' : 's'}
                        {' '}have no open work order, so a live &ldquo;AI raises a work
                        order&rdquo; demo has a target.
                      </>
                    ) : (
                      <>
                        No overdue machine is left without an open work order, so
                        the create endpoint will answer 409 for all of them.
                        Raise &ldquo;Overdue machines held back&rdquo; if you need a live
                        AI demo.
                      </>
                    )}
                  </div>

                  <div className="pt-1">
                    <a
                      href="/machines"
                      className="text-sm font-medium text-primary-on-soft hover:underline"
                    >
                      Open the machine dashboard &rarr;
                    </a>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </main>
    </div>
  );
};

export default DemoReset;
