#!/usr/bin/python
# -*- coding: UTF-8 -*-

#============================================================================================
#  check-syno-backup :
#    Command line tool to get Synology Backup job status information
#    (to be used as a "plugin" with Nagios, or any other network monitoring environment)
# 
#    It scans Synology Backup logs for a specific job name, then returns information
#    about completion of the last occurrence of that job.
#
#  Initial version made by : Carolyn DESPRES (despres@ece.fr)
#  Current maintainer      : Toussaint OTTAVI (t.ottavi@medi.fr)
#
#============================================================================================

#============================================================================================
#    This is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>. 
#============================================================================================

#============================================================================================
# Imports (ensure all modules are installed on your system) 
#============================================================================================

import sys, getopt, string, time, os
from datetime import timedelta, datetime


#============================================================================================
# Version Number
#============================================================================================

ProgramName = "check_syno_backup.py"
AuthorName = "Carolyn DESPRES & Toussaint OTTAVI"
Version = "3.0"
VersionDate = "26/08/2016"

VERSION_HISTORY = '''

- 1.0 (25/08/2014) : 
  - Initial release for DSM 4.x by Carolyn DESPRES, as a training project

- 2.0.4 (15/01/2015) : 
  - Maintenance release by T. OTTAVI
  - Added compatibility with DSM 5.1 log files 
    (netbackup logs are now in synobackup.log, and no more in synonetbkp.log)
  - Bug when processing parallel NetBackup tasks
  - Improvements in test logic
  - Improvement in log file detection logic (in case of unix rights restrictions)

- 2.0.5 (26/01/2015) :
  - Bug when task name appears in other situations than start/end (ie renaming of task)
  - Bug warning/critical days check
  
- 2.1.0 (16/07/2015) :
  - Checked compatibility with DSM 5.2 log files
  - Renamed to "check_syno_backup" to start handling other backup types (only "Network to share" was supported in previous versions) 
  - Added support for "Local to volume" backups

- 2.1.1 (16/11/2015) :
  - Added compatibility with "Network to volume"
  
- 2.1.2 (24/05/2016) :
  - DSM6 compatibility : [Local to volume] is renamed to [Local] in the log file
  
- 2.1.3 (26/08/2016) :
  - DSM6 compatibility : [Network to share] is renamed to [Network] 
 
- 3.0 (26/08/2016) :
  - First Github public release
      
TODO:
  - Does not work in case of log rotation (/etc/synolog/synobackup.log.0)
  - Check version rotation completion / errors
  - Documentation for Nagios / NRPE installation
'''


#============================================================================================
# Default values
#============================================================================================

# Threshold values for task age (in days)
MAX_WARNING_DAYS = 1
MAX_CRITICAL_DAYS = 3

# Threshold values for execution time (in minutes)
MAX_WARNING_MINUTES = 60
MAX_CRITICAL_MINUTES = 180


#============================================================================================
# Nagios return codes 
#============================================================================================

NAGIOS_CODES = {'OK': 0,
                'WARNING': 1,
                'CRITICAL': 2,
                'UNKNOWN': 3,
                'DEPENDENT': 4}


################################################################################
#                                                                              #
#                              HELP / LICENSING                                #
#                                                                              # 
################################################################################ 

#============================================================================================
# Print one-line usage description 
#============================================================================================

def usage():
  nagios_return('UNKNOWN', 'Syntax Error - use %s -h for help' % (ProgramName))
   

#============================================================================================
# Print detailed help 
#============================================================================================

def helptext():
    
  print "\n%s v%s (%s) - (c) %s" % (ProgramName, Version, VersionDate, AuthorName) 
   
  text = '''
  This is free software. This program comes with ABSOLUTELY NO WARRANTY.
  
  Scans Synology Backup logs for a specific job, then returns information
  about completion of the last occurrence of that job.'''
  print text
  print '\nUsage : %s [Options] -t "task" [Switches]  '% (ProgramName)
 
  text = '''
  Required arguments is :
      -t , --task : task name
  Valid options are : 
      -h, --help : Displays this help text
      -l, --licensing : Displays licensing information
      -d, --debug : Displays debug / debugging information     
  Valid switches are :
      -w<n> , --warning: warning if las result is older than <n> days
      -c<n>, --critical : critical if last result is older than <n> days 
      -W<n> , --w_execution: warning if execution time is longer than <n> minutes
      -C<n> , --c_execution: critical if execution time is longer than <n> minutes

 '''
  print text
  
  sys.exit(NAGIOS_CODES["UNKNOWN"])


#============================================================================================
# Print licensing information 
#============================================================================================

def licensing():
  print
  print "  %s v%s (%s) - (c) %s" % (ProgramName, Version, VersionDate, AuthorName)
  
  Licensing = '''
  This is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.
  
  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.
  
  You should have received a copy of the GNU General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.
  '''
  print Licensing
  print  "Type %s -h for Help" % (ProgramName)
  print
  
  sys.exit(NAGIOS_CODES["UNKNOWN"])
  
    
#============================================================================================
# Print debug/verbose information
#============================================================================================

def PrintDebug (text):
  if debug: 
    print text
        
        
#============================================================================================
# Print the return message and exits with the specified return code 
#============================================================================================

def nagios_return(code, message):
    
  print code + ": " + message
  sys.exit(NAGIOS_CODES[code])

        
################################################################################
#                                                                              #
#                            STRING PROCESSING                                 #
#                                                                              # 
################################################################################        

#===============================================================================
# Return string from separator to end
#===============================================================================

def StringAfter(s, separator):
  try:
    tmp = s.partition(separator)[2]
  except:
    tmp = ""  
  return tmp

        
#===============================================================================
# Return string between two separators
#===============================================================================

def StringBetween(s, sep1, sep2):
  try:
    tmp = s[string.find(s , sep1)+1:string.find(s, sep2)]
  except:
    tmp = ''
  return tmp


#===============================================================================
# Returns True if string contains substring
#===============================================================================

def StringContains (s, sub):
  flag = False
  if s<>"":
    if string.find(s, sub)<>-1:
      flag= True 
  return flag       


#===============================================================================
# Remove non-ASCII characters and replace them by "?"
#===============================================================================

def StringNormalize (s):
  ret = ''
  try:
    for c in s:
      cc=ord(c)
      if cc>=32 and cc<127:
        r = c
      else:
        r = '?'
      ret = ret + r 
  except:
    pass
  return ret
  
  
#===============================================================================
# Display a datetime in readable form
#===============================================================================
  
# Change according to your country / habits. 
# Here : DD/MM/YYYY HH:MM:SS
  
def DisplayDateTime (dt):
  try:
    dd = "%02d" % (dt.day)
    mm = "%02d" % (dt.month)
    yy = "%s" % dt.year
    ho = "%02d" % (dt.hour)
    mi = "%02d" % (dt.minute)
    se = "%02d" % (dt.second)
    ret = "%s/%s/%s %s:%s:%s" % (dd, mm, yy, ho, mi, se)
  except:
    ret = "<Display Date Error>"
  return ret  

 
################################################################################
#                                                                              #
#                          LOG FILE PROCESSING                                 #
#                                                                              # 
################################################################################    
     
#============================================================================================
# Extract task name from a line 
#============================================================================================

def GetTaskName(line, dsm):
  try:
    line2 = line if dsm==50 else StringAfter (line, "]")
    name = StringBetween (line2, '[', ']')
  except:
    PrintDebug("GetTaskName : Exception processing line")
    name="<Unknown>"
  return name


#============================================================================================
# Find error message in a line
#============================================================================================

def GetProblemDetails (line, dsm):
  try:
    if dsm == 50 :
      msgtmp = StringBetween (line, "SYSTEM: ", '[')
      msg = StringNormalize(msgtmp)
      
    elif dsm == 51 :
      tmp = StringAfter (line, ']')
      msg = StringAfter (tmp, ']')

    else:
      msg = "<Error>"
        
  except:
    msg = "<Unable to get error description>"
       
  return msg


#============================================================================================
# Extract date and time from a task line
#============================================================================================

#    return a datetime type  (year, month , day, hour, minute, second)
#    Ex: datetime(1000, 1, 2, 3, 4, 5) is 2 january 1000 03:04:05

def GetDateTime(line):
  try:
    s1 =string.split(line)
    
    s2=string.split(s1[1],"/")
    y = int(s2[0])
    mo = int(s2[1])
    d = int(s2[2])
    
    s3=string.split(s1[2],":")
    h = int(s3[0])
    mi = int(s3[1])
    s = int(s3[2])
    
    PrintDebug ('Year: %d, Month: %d, Day: %d, Hour: %d, Minute: %d, Second: %d' % (y,mo,d,h,mi,s))
    time=datetime(y,mo,d,h,mi,s) 
  
  except:
    PrintDebug("Exception : Unable to extract date and time")
    time=datetime(1000, 1, 1, 1, 1,1)  

  return time #type datetime  (year, month , day, hour, minute, second)


#============================================================================================
# Check DSM version. Returns version number and path to the right log file
#============================================================================================

# Path for Synology log files

PATH_LOGFILE_DSM50 = "/var/log/synolog/synonetbkp.log"
PATH_LOGFILE_DSM51 = "/var/log/synolog/synobackup.log"

# If synobackup.log is present, and contains "[Network to share]" jobs, then we are under DSM 5.1
# If synobackup.log is absent, or does not contain "[Network to share]", then we are under DSM <5.1, we must use synonetbkp.log


def CheckDSMVersion():

  DSM = 0
  
  # Check if we are under DSM 5.1+
  
  PATH = PATH_LOGFILE_DSM51
  PrintDebug ("Checking existence of file %s" % (PATH))
  try:
    if os.path.exists(PATH):
      PrintDebug ("Found %s log file " % (PATH))
      try:
        f = open (PATH, 'r')    
        for line in f:
          if    StringContains (line, "[Network to share]") \
             or StringContains (line, "[Network to volume]") \
             or StringContains (line, "[Local to volume]")  \
             or StringContains (line, "[Local]") \
             or StringContains (line, "[Network]"):
            DSM=51
            PrintDebug ("File %s contains Backup log data." % (PATH))
            return DSM, PATH  
        PrintDebug ("File %s is readable, but it does not contain NetBackup data" % (PATH))
        f.close()        
      except:
        PrintDebug ("Exception reading file %s" % (PATH))      
    else:
      PrintDebug ("File %s not found." % (PATH))   
  except:
    PrintDebug ("Exception checking file path for %s" % (PATH))      
    
  # Check if we are under DSM <5.1
  
  PATH = PATH_LOGFILE_DSM50  
  PrintDebug ("Checking existence of file %s" % (PATH))  
  try:
    if os.path.exists(PATH):
      PrintDebug ("Found %s log file" % (PATH))
      try:
        f = open (PATH, 'r')    
        for line in f:
          if StringContains (line, "Network Backup started to backup task"):
            DSM=50
            PrintDebug ("File %s contains NetBackup log data." % (PATH))
            return DSM, PATH  
        PrintDebug ("File %s is readable, but it does not contain NetBackup data" % (PATH))
        f.close()        
      except:
        PrintDebug ("Exception reading file %s" % (PATH))      
    else:
      PrintDebug ("File %s not found." % (PATH))   
      
  except:
    PrintDebug ("Exception checking file path for %s. Check unix path and rights" % (PATH))      
  
  # None of them found or readable
  
  PrintDebug ("Unable to check presence of log files %s or %s" % (PATH_LOGFILE_DSM50, PATH_LOGFILE_DSM51))
  PATH=""
  return DSM, PATH


#============================================================================================
#  Parse log file and extract informations about log jobs
#============================================================================================
    
# Returns a table. Each element is a dictionnary type, containing informations about a job.
# Keys are : 'name','start', 'duration', 'status', 'error'
# 'status' can take only two values: 'OK' or 'CRITICAL'

def ParseLogFile (path, dsm):
    
  TABLE_FINISHED = []    # Table of finished tasks
  TABLE_PROCESSING = []  # Temporary table for processing tasks

  PrintDebug ("Parsing file %s with DSM version %d" % (path, dsm))
     
  try:
    f = open(path, 'r')    
    
    for line in f:
    
      PrintDebug ('--------------------------------------------------------------')
      PrintDebug ("Processing line:")
      PrintDebug (line)
      
      # ===== Is it a NetBackup task ? (DSM5.0 and lower log contains only NetBackup tasks, but DSM >5.1 contains other backup types)
      
      if dsm==50 \
      or (dsm==51 and (   StringContains (line, "[Network to share]") \
                       or StringContains (line, "[Network to volume]") \
                       or StringContains (line, "[Local to volume]") \
                       or StringContains (line, "[Local]") \
                       or StringContains (line, "[Network]"))) :
      
        PrintDebug ("    OK, this is a recognised Backup task line")
      
        name = GetTaskName(line, dsm)
        PrintDebug ("    Found task name : %s" % (name))
      
        # ---------- Is it the beginning of a task ?
        
        starttext = "Network Backup started to backup task" if dsm==50 else "Backup task started."
        if StringContains (line, starttext) :
          
          PrintDebug ("    -> This is task start")
          starttime = GetDateTime(line)
          name = GetTaskName(line, dsm)
          PrintDebug ("       Task [%s] started at : %s" % (name, DisplayDateTime(starttime))) 

          status = 'UNKNOWN'
          problem = "None"
          endtime = datetime(3000, 1, 1, 1, 1,1)
          duration = 0          
          
          # Is the task already in the processing table ?

          Found = False
          for t in TABLE_PROCESSING:
            if t['name'] == name:

              # If found, update that task data
              
              PrintDebug ('       WARNING, found previously started task [%s]. Updating data.' % name)              
              t['start'] = starttime
              t['end'] = endtime
              t['duration'] = duration
              t['status'] = status
              t['error'] = problem
              Found = True
          
          # If not found, create new dictionary entry in the processing table

          if not (Found) :          
            dct = dict([('name', name), ('start',starttime), ('end', endtime), ('duration', duration), ('status', status), ('error', problem)] )
            TABLE_PROCESSING.append(dct)
            PrintDebug ("       Added task [%s] to the processing table" % name)
            
            
        #  ---------- is it an error line ?
        
        elif StringContains (line, "err") :
          
          PrintDebug ("    -> This is an error line")
          name = GetTaskName(line, dsm)
          
          # Is this task in our processing table ?
          
          for t in TABLE_PROCESSING:
            if t['name'] == name:
              PrintDebug ('       Found previously started task [%s]' % name)      
              
              # Add to the finished tasks table

              t2 = t
              t2['status'] = 'CRITICAL'
              t2['problem'] = GetProblemDetails (line, dsm) 
              t2['end'] = GetDateTime (line)
              t2['duration'] = t2['end'] - t2['start']
              TABLE_FINISHED.append(t2)
              TABLE_PROCESSING.remove (t)
              PrintDebug ('       Added to the finished tasks list with CRITICAL status')
              break
            
            
        # ---------- Is it the end of a task ?
          
        elif StringContains (line, "finished") :
          
          PrintDebug ("    -> This the normal end of a task")
          name = GetTaskName(line, dsm)

          # Is this task in our processing table ?
          
          for t in TABLE_PROCESSING:
            if t['name'] == name:
              PrintDebug ('       Found previously started task [%s]' % name)      
              
              # Add to the finished tasks table

              t2 = t
              t2['status'] = 'OK'
              t2['problem'] = "Task finished successfully" 
              t2['end'] = GetDateTime (line)
              t2['duration'] = t2['end'] - t2['start']
              TABLE_FINISHED.append(t2)
              TABLE_PROCESSING.remove (t)
              PrintDebug ('       Added to the finished tasks list with OK status')
              break             
    
      PrintDebug ('----- Tasks being processed : %d ----- Tasks finished : %d -----' % (len (TABLE_PROCESSING), len(TABLE_FINISHED)))
      
    PrintDebug ('--------------------------------------------------------------')
    f.close()
  except:
    PrintDebug ("Exception parsing log file %s" %(path))
      
  # return a table of finished tasks (each task is a dict)   
  
  return TABLE_FINISHED


#============================================================================================
# Find the most recent task with given name whose status is OK 
#============================================================================================

def FindLatestTask (table, taskname):
    
  lastdate= datetime(1200,4,4,4,4,4)  # datetime(years, months, days, hours, minutes, secondes)

  exists = False     # Flag if we found some task with the specified name
  found = {}         # contains last good task found (empty if none)
  
  PrintDebug ("Searching for latest occurrence of task %s " % (taskname))
  try:      
    for dct in table:
      if dct['name'] == taskname :
        exists = True
        if dct['status'] == 'OK':
          if dct['start'] > lastdate:
            lastdate = dct ['start']
            found = dct
  except:
    found = {}
    PrintDebug ("Exception - Unable to locate latest Backup task")            
              
  return exists, found            


#============================================================================================
# Debug : Print list of task names found  
#============================================================================================
              
def PrintTaskNames (table):

  listnames = []  
  PrintDebug ('List of Backup tasks found in log :')
  try:
    for dic in table:
      if dic['name'] not in listnames:
        listnames.append(dic['name'])
        PrintDebug( "   " + dic['name'])
  except:
    PrintDebug ("Exception printing list of tasks")



#============================================================================================
# Debug : Print all tasks found within the last nbday days
#============================================================================================

def PrintTasksSince (table, taskname, nbday):
    
  print "List of Backup tasks since %d days :" % (nbday)
  
  try:
    for dic in table:
      if dic['name'] == taskname:
        if dic['start'] > datetime.now()-timedelta(days=nbday):
          print "  Task: %s, started: %s, status: %s, execution time: %s" % (dic['name'], DisplayDateTime(dic['start']), dic['status'], str(dic['duration']))
  except:
    PrintDebug("Exception during  display of last tasks")


#============================================================================================
# Debug : Print details of a task
#============================================================================================

def PrintTaskDetails (task):

  print "========== Details of task =========="
  print "  Task name  : %s" % task['name']
  print "  Start time : %s" % DisplayDateTime(task['start'])
  print "  End time   : %s" % DisplayDateTime(task['end'])
  print "  Duration   : %s" % task['duration']
  print "  Status     : %s" % task['status']
  print "  Details    : %s" % task['error']
  print "===="
          
 
#============================================================================================
# Test task, and compare with threshold values
#============================================================================================

def CheckThreshold(task):

  message = ""
  code = 'UNKNOWN'              # Overall Nagios return code
  code_age = 'UNKNOWN'          # Partial return code about the age of the last good task
  code_duration = 'UNKNOWN'     # Partial return code about the duration of the last good task


  # Is the last good task recent enough ?
  
  taskdate = DisplayDateTime (lasttask['end'])
  age_timedelta = datetime.now()-lasttask['end']     # Age of the latest task
  age_days = age_timedelta.total_seconds() / 86400       # Age in days  
  PrintDebug (" The last task is %d days old "% (age_days))
  
  if age_days > MAX_CRITICAL_DAYS:
    code_age = 'CRITICAL'
    message = "[CRIT] Last good result (%s) is more than %d days old" % (taskdate, MAX_CRITICAL_DAYS)
  
  elif age_days > MAX_WARNING_DAYS:
    code_age = 'WARNING'
    message = "[WARN] Last good result (%s) is more than %d days old" % (taskdate, MAX_WARNING_DAYS)
  
  elif age_days < 0 :
    code_age = 'UNKNOWN'
    message = message + "Task date error, older than now"
  
  else :
    code_age = 'OK'
    message = "Last good result (%s) is within the last %d days" % (taskdate, MAX_WARNING_DAYS) 
  

  # Is the duration of the last good task within the accepted bounds ?

  duration = lasttask['duration'].total_seconds() / 60      # Duration in minutes
  
  if duration > MAX_CRITICAL_MINUTES:
    code_duration = 'CRITICAL'
    message = message + ", [CRIT] Execution time (%d min) is more than %d minutes" % (duration, MAX_CRITICAL_MINUTES)

  elif duration > MAX_WARNING_MINUTES:
    code_duration = 'WARNING'
    message = message + ", [WARN] Execution time (%d min) is more than %d minutes" % (duration, MAX_WARNING_MINUTES)
  
  elif duration <  0:
    code_duration = 'UNKNOWN'
    message = message + ", Error, execution time is negative"
  
  else:
    code_duration = 'OK'
    message = message + ", Execution time (%d min) is within bounds" % (duration)
    
      
  # Final response code
      
  if code_age =='CRITICAL' or code_duration =='CRITICAL' :
    code ='CRITICAL' 
  
  elif code_age == 'WARNING' or code_duration == 'WARNING':
    code ='WARNING'

  elif code_age == 'UNKNOWN' or code_duration == 'UNKNOWN':
    code ='UNKNOWN'

  elif code_age == 'OK' and code_duration == 'OK':
    code ='OK'
      
  else:
    code ='UNKNOWN'
    message = "Error in check logic. This should not happen. See source code."
  
  
  # Add performance data to the output string
  
  if code == "OK":
    perfdata = "|'execution_time'=%dm;%d;%d;%d;%d" % (duration, MAX_WARNING_MINUTES, MAX_CRITICAL_MINUTES, 0, 0)
    message = message + perfdata   
       
  return code, message
  

############################################################################################
#                                                                                          #
#                                         M A I N                                          #
#                                                                                          #
############################################################################################  

if __name__ == "__main__":
    
  #---------------------------------------------------------- Variable initialisation

  debug=False
  taskname = "Empty"

  #-------------------------------------------------- Processing command line options
  if len(sys.argv) <=1 :
      PrintDebug("No argument")
      usage()
        
  try:
    opts, args = getopt.getopt(sys.argv[1:], "hldvt:w:c:W:C:", ["help","licensing","debug", "verbose", "task=", "warning=", "critical=", "w_execution=", "c_execution="])
  except getopt.GetoptError, err:
    PrintDebug("Exception getting arguments")
    usage()
        
  for option, value in opts:
    if option in ("-h", "--help"):
      helptext()
    elif option in ("-l", "--licensing"):
      licensing()
    elif option in ("-d", "--debug", "-v", "--verbose"):
      debug = True
    elif option in ("-t", "--task"):
      taskname = value
        
    elif option in ('-w', "--warning"):
      try:
        MAX_WARNING_DAYS = int(value)
        PrintDebug ("Warning date threshold is now set to %d days" % (MAX_WARNING_DAYS))  
      except:
        PrintDebug( "Invalid value %s for -w (warning) : must be integer. Ignored")
            
    elif option in ('-c', "--critical"):
      try:
        MAX_CRITICAL_DAYS = int(value)
        PrintDebug ("Critical date threshold is now set to %d days" % (MAX_CRITICAL_DAYS))  
      except:
        PrintDebug(  "Invalid value %s for -c (critical) : must be integer. Ignored")
             
    elif option in ('-W', "--w_execution"):
      try:
        MAX_WARNING_MINUTES = int(value)
        PrintDebug ("Warning execution time threshold is now set to %d minutes" % (MAX_WARNING_MINUTES))  
      except:
        PrintDebug(  "Invalid value %s for -W (w_execution) : must be integer. Ignored")
             
    elif option in ('-C', "--c_execution"):
      try:
        MAX_CRITICAL_MINUTES = int(value)
        PrintDebug ("Critical execution time threshold is now set to %d minutes" % (MAX_CRITICAL_MINUTES))  
      except:
        PrintDebug( "Invalid value %s for -C (c_execution) : must be integer. Ignored")
                
  #-------------------------------------------------------------- Checking validity of parameters 
  
  if taskname == "Empty":
    nagios_return('UNKNOWN', "Argument missing: name of task - use %s -h for help" % (ProgramName))
  PrintDebug("Task name to ckeck is: " + taskname)


  # Check DSM log file version

  DSM, PATH = CheckDSMVersion()
  if DSM == 0 :
    nagios_return('UNKNOWN', 'Unable to read log files. Check Unix permissions on /var/log/synolog (see doc)')
  
  PrintDebug ("DSM version is %s, log file to be processed is %s" % (DSM, PATH))
  
  
  #-------------------------------------------------------------- Process DSM log file 

  # Parse file, returns a table of tasks
  
  table = ParseLogFile (PATH, DSM)             
  if debug:
    PrintTaskNames (table)
  
  # Find most recent task of given name whose status is OK
      
  exists, lasttask = FindLatestTask (table, taskname)
  
  if exists == False:
    code = "UNKNOWN"
    message = "Did not find any Backup task with name [%s]" %(taskname)
    
  elif lasttask == {}:
    code = "CRITICAL"
    message = "Task [%s] found in the log, but all occurrences are FAILED" %(taskname)
  
  else:
    if debug:
      PrintTasksSince(table, taskname, MAX_CRITICAL_DAYS )
      print
      print "Last occurrence of task :"
      PrintTaskDetails (lasttask)
      
    # Check if task duration is within bounds    
  
    code, message = CheckThreshold (lasttask)


  #------------------------------------------- exit with return code and message
  
  nagios_return(code, message)
