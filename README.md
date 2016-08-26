# check syno backup #

## What is it ? ##

This is a python script to get Synology NAS backup job status information. It's intended to be used as a "plugin" for Nagios, or any other monitoring environment. 

## Author ##
This software is (c) Toussaint OTTAVI, bc-109 Soft

## How does it work ? ##

It runs on the Synology NAS. It scans the main Synology Backup log for a specific job name, then returns information about completion of the last occurrence of that job.

## How  to use it ? ##
It's a command-line python script. Just copy it to your Synology NAS server via ssh, and run it with the -h switch to get help :

	check_syno_backup -h

A typical command line is :

	check_syno_backup.py -t "My backup task" -W 30 -C 60 

For diagnostic purposes, just add the -v (verbose) switch. This will display useful troubleshooting information :

	check_syno_backup.py -t "My backup task" -W 30 -C 60 -v


## Examples of outputs : ##
Here are some sample outputs :

`OK: Last good result (26/08/2016 04:02:43) is within the last 1 days, Execution time (2 min) is within bounds` 
`WARNING: Last good result (26/08/2016 07:27:45) is within the last 1 days, [WARN] Execution time (57 min) is more than 30 minutes`
`CRITICAL: [CRIT] Last good result (20/08/2016 16:33:16) is more than 3 days old, [CRIT] Execution time (153 min) is more than 120 minutes`  
`UNKNOWN: Did not find any Backup task with name [Sauvegarde locale]`


## How to use it with Nagios ? ##

In order to get the results from a Nagios server, this software must be run on the Synology NAS through NRPE (Nagios Remote Plugin Executor).

## Installation and configuration with Nagios and NRPE ##

todo...

## License ##
This is free software: you can redistribute it and/or modifyit under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.  If not, see <http://www.gnu.org/licenses/>.