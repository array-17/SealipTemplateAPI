from adapters import getAllJobs, jobClass
class JobRunner:
    def __init__(self,ActionClass, ResultsClasses):
        self.ActionClass = ActionClass
        self.ResultsClasses = ResultsClasses

    
    def run_loop(self):
        import time
        while True:
            print("JobRunner: Checking for queued cases...")
            cases = self.get_cases()
            if len(cases) == 0:
                time.sleep(5)
                continue
            for case in cases:
                # Only run cases that are Queued, not already Running/Completed/Failed
                if case.get_status() == "Queued":
                    case.runCase()
            # Small delay to avoid tight loop
            time.sleep(1)

    def get_cases(self):
        jobs = getAllJobs(self.ActionClass, self.ResultsClasses)
        all_cases = []
        for job in jobs:
            if( not job.isCompleted() ):
                all_cases.extend(job.get_cases())
        return all_cases