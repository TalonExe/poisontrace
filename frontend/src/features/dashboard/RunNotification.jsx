import { useEffect } from "react";
import { sessionGeneration } from "../../lib/http/sessionExpiry";
import { observeInvestigationJobs } from "./investigationJobObserver";

const statusLabels = {
  queued: "queued",
  active: "running",
  completed: "complete",
  failed: "failed",
  interrupted: "interrupted",
};

function isBusy(job) {
  return job?.status === "queued" || job?.status === "active";
}

export function RunNotification({ runner, notice, setNotice, onResults }) {
  const job = notice?.job;
  const busy = isBusy(job);
  const kind = notice?.kind;
  const jobId = job?.job_id;

  useEffect(() => {
    let active = true;
    const generation = sessionGeneration();
    runner.listInvestigationJobs().then((jobs) => {
      if (!active || generation !== sessionGeneration()) return;
      const current = jobs.find((item) => isBusy(item) &&
        !item.campaign_id && item.workflow !== "metadata-v1");
      if (current) setNotice((previous) => previous ?? {
        kind: current.group_id ? "group" : "single",
        job: current,
      });
    }).catch(() => {});
    return () => { active = false; };
  }, [runner, setNotice]);

  useEffect(() => {
    if (!busy || !jobId) return;
    return observeInvestigationJobs({
      runner,
      kind,
      jobId,
      onUpdate: ({ job: current, progress }) => {
        setNotice((previous) => previous?.job?.job_id === jobId
          ? { ...previous, job: current, progress }
          : previous);
      },
      onError: () => {},
    });
  }, [runner, busy, kind, jobId, setNotice]);

  if (!notice) return null;

  const group = kind === "group";
  const label = group ? "Matched group" : "Single run";
  const pending = busy || (!job && !notice.error);
  const outcome = group
    ? job?.group_id && `/results/groups/${encodeURIComponent(job.group_id)}`
    : job?.run_id && `/results/runs/${encodeURIComponent(job.run_id)}`;
  const title = job ? `${label} ${statusLabels[job.status] ?? job.status}`
    : notice.error ? `${label} could not start` : `Starting ${label.toLowerCase()}…`;

  function openOutcome() {
    setNotice(null);
    onResults(outcome);
  }

  return <section className="run-notification" aria-label="Run notification">
    <span className="run-notification-icon" data-pending={pending} data-completed={job?.status === "completed"} aria-hidden="true">
      {!pending && (job?.status === "completed" ? "✓" : "!")}
    </span>
    <div>
      <div role="status" aria-atomic="true">
        <strong>{title}</strong>
        {notice.error && <p>{notice.error}</p>}
        {notice.progress && <p>{notice.progress.completed} completed</p>}
        {job?.status === "interrupted" && <p>The execution outcome is uncertain.</p>}
      </div>
      {!pending && outcome && <button type="button" className="run-button" onClick={openOutcome}>See the results</button>}
    </div>
    {!pending && <button type="button" className="run-notification-dismiss" aria-label="Dismiss run notification" onClick={() => setNotice(null)}>×</button>}
  </section>;
}
