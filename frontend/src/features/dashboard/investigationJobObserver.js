function isBusy(job) {
  return job.status === "queued" || job.status === "active";
}

export function observeInvestigationJobs({ runner, kind, jobId, onUpdate, onError }) {
  const groupJobs = kind === "group";
  let active = true;
  let timer;

  async function poll() {
    try {
      const jobs = await runner.listInvestigationJobs();
      if (!active) return;
      const matching = jobs.filter((job) => {
        if (jobId) return job.job_id === jobId;
        if (groupJobs) return Boolean(job.group_id);
        if (kind === "campaign") return Boolean(job.campaign_id) && job.ordinal == null;
        return !job.group_id && !job.campaign_id && Boolean(job.workflow === "metadata-v1") === (kind === "metadata");
      });
      const job = matching.find(isBusy) || matching[0];
      if (job) {
        const update = { job, busy: isBusy(job) };
        if (groupJobs) {
          const group = await runner.getRunGroup(job.group_id);
          if (!active) return;
          update.progress = group.progress;
        }
        onUpdate(update);
      }
    } catch (error) {
      if (active) onError(error);
    }
    if (active) timer = setTimeout(poll, 1000);
  }

  poll();
  return () => {
    active = false;
    clearTimeout(timer);
  };
}
