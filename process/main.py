import config as conf
import job_manager as jm
import time as tm

def main():
    job_manager = jm.JobManager()
    while (True):
        tm.sleep(conf.sleep_time_in_seconds) # Check for new jobs at intervals.
        job_manager.run_next_job()

if __name__ == "__main__":
    main()
