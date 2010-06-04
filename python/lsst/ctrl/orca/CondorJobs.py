#!/usr/bin/env python

import os
import sys
import re
import time
from lsst.pex.logging import Log


#
# This class is highly dependent on the output of the condor commands 
# condor_submit and condor_q
#
class CondorJobs:
    def __init__(self, logger):
        self.logger = logger
        self.logger.log(Log.DEBUG, "CondorJobs:__init__")
        return


    # submit a condor file, and return the job number associated with it.
    # expected output:
    # Submitting job(s).
    # Logging submit event(s).
    # 1 job(s) submitted to cluster 1317.
    
    def submitJob(self, condorFile):
        self.logger.log(Log.DEBUG, "CondorJobs:submitJob")
        clusterexp = re.compile("1 job\(s\) submitted to cluster (\d+).")
    
        submitRequest = "condor_submit %s" % condorFile
    
        pop = os.popen(submitRequest, "r")
    
        line = pop.readline()
        line = pop.readline()
        line = pop.readline()
        num = clusterexp.findall(line)
        if len(num) == 0:
            return None
        print "submitted job file %s.  It is job # %s" % (condorFile, num[0])
        return num[0]
    
    
    
    # wait for a condor job to reach it's run state.
    # expected output:
    #-- Submitter: srp@lsst6.ncsa.uiuc.edu : <141.142.15.103:40900> : lsst6.ncsa.uiuc.edu
    # ID      OWNER            SUBMITTED     RUN_TIME ST PRI SIZE CMD               
    #1016.0   srp             5/24 09:17   0+00:00:00 I  0   0.0  launch_joboffices_
    #1017.0   srp             5/24 09:18   0+00:00:00 R  0   0.0  launch_joboffices_
    
    def waitForJobToRun(self, num):
        self.logger.log(Log.DEBUG, "CondorJobs:waitForJobToRun")
        jobNum = "%s.0" % num
        queueExp = re.compile("\S+")
        cJobSeen = 0
        print "waiting for job %s to run." % num
        print "this might take a few minutes"
        secondsWaited = 0
        while 1:
            pop = os.popen("condor_q", "r")
            bJobSeenNow = False
            if (secondsWaited > 0) and ((secondsWaited % 60) == 0):
                minutes = secondsWaited/60
                print "Waited %d minute%s so far. Still waiting for job %s to run." % ((secondsWaited / 60), ("" if (minutes == 1) else "s"), num)
            while 1:
                line = pop.readline()
                if not line:
                    break
                values = queueExp.findall(line)
                if len(values) == 0:
                    continue
                runstate = values[5]
                if (values[0] == jobNum):
                    cJobSeen = cJobSeen + 1
                    bJobSeenNow = True
                if (values[0] == jobNum) and (runstate == 'R'):
                    print values
                    pop.close()
                    print "Job %s is now being run." % num
                    return 'R'
                if (values[0] == jobNum) and (runstate == 'H'):
                    pop.close()
                    # throw exception here
                    print "Job %s is being held.  Please review the logs." % num
                    return 'H'
                if (values[0] == jobNum) and (runstate == 'X'):
                    print values
                    pop.close()
                    # throw exception here
                    print "Saw job %s, but it was being aborted" % num
                    return 'X'
            # check to see if we've seen the job before, but that
            # it disappeared
            if (cJobSeen > 0) and (bJobSeenNow == False):
                pop.close()
                print "Was monitoring job %s, but it exitted." % num
                # throw exception
                return None
            pop.close()
            time.sleep(1)
            secondsWaited = secondsWaited + 1

    def waitForAllJobsToRun(self, numList):
        self.logger.log(Log.DEBUG, "CondorJobs:waitForAllJobsToRun")
        queueExp = re.compile("\S+")
        jobList = list(numList)
        while 1:
            pop = os.popen("condor_q", "r")
            while 1:
                line = pop.readline()
                if not line:
                    break
                values = queueExp.findall(line)
                if len(values) == 0:
                    continue
                jobNum = values[0]
                runstate = values[5]
                for jobEntry in jobList:
                    jobId = "%s.0" % jobEntry
                    if (jobNum == jobId) and (runstate == 'R'):
                        jobList = [job for job in jobList if job[:] != jobEntry]
                        if len(jobList) == 0:
                            return
                        break
                    else:
                        continue
                    if (jobNum == jobEntry) and (runstate == 'H'):
                        pop.close()
                        # throw exception here
                        return
            pop.close()
            time.sleep(1)
