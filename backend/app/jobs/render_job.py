"""Entry point for a detached bulk-render process:

    python -m app.jobs.render_job <job_id>

Started by app.services.render_jobs.start_job with the service's environment.
"""
import sys

from ..logging_config import configure_logging, get_logger
from ..services.render_jobs import run_job


def main() -> int:
    configure_logging()
    log = get_logger("app.jobs.render_job")
    job_id = int(sys.argv[1])
    # Never pass reserved LogRecord names (name, msg, created, …) in extra (Gotcha #12).
    log.info("render job started", extra={"event": "render_job_started", "job_id": job_id})
    run_job(job_id)
    log.info("render job finished", extra={"event": "render_job_finished", "job_id": job_id})
    return 0


if __name__ == "__main__":
    sys.exit(main())
