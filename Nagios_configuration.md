# check syno backup - Nagios configuration #

## What is it ? ##

check_syno_backup is a plugin, to be used in a network monitoring environment, such as Nagios. 

This document explains how to configure and use it with Nagios. For more information see the main [README.md](README.md "README file")

With slight adaptations, this plugin can be used with any other monitoring software, such as Shinken, Icinga, Naemon, etc... 


## Pre-requisites ##

In order to use this plugin, you must have :

- a running Nagios server (or Nagios clone : Icinga, Shinken, Naemon, etc...)
- a Synology NAS, under DSM5 or DSM6, with Bootstrap and NRPE already installed and running


## Installing the plugin ##

Just copy the check_syno_backup.py on your NAS, in the /opt/libexec directory. Don't forget to make it executable :

    chmod +x /opt/libexec/check_syno_backup.py
    

## Nagios server configuration ##

Here are some configuration samples for your Nagios server :

Object definition :

    define host{
      use        linux-server
      host_name  MY_SYNOLOGY_NAS   
      alias      This is the name of my Sonology NAS   
      address    192.168.1.2
      notes_url  http://$HOSTADDRESS 
      }
    
    define service {
      use                  template-syno-backup
      host_name            MY_SYNOLOGY_NAS
      service_description  My Synology NAS - My Backup job name
      }
    

Template definition :

    define service{
      name                   template-syno-backup
      use                    generic-service
      service_description    Synology - Sauvegarde 
      check_command          check_nrpe_nossl!-c syno_backup -t 60
      icon_image             backup.gif
      service_groups         Synology Backup Group
      normal_check_interval  60
      retry_check_interval   60
      register   0
      }
    
## NRPE client configuration on the Synology NAS ##

Here's what to add in your /opt/etc/nrpe.cfg file :

    command[syno_backup]=/opt/libexec/check_syno_backup.py -t "My Syno Backup Task Name" -W 60 -C 120
    

## File access rights considerations on the Synology NAS ##

This plugin works by reading the **/var/log/synolog/synobackup.log**. For that purpose, the NRPE user must have read access on that file, and on the parent directories. 

On DSM5 and below, it was possible to tune the syslog-ng.conf file, so that the synobackup.log is written with the correct rights. This (old) method does not seem to work anymore under DSM6, so I won't document it. 

The following method is merely a hack, but I didn't find anything better under DSM6. This method should work both in DSM5 and DSM6 :

**Step 1 :** Change the rignts of the synolog directory to allow reading/browsing for anyone

    chmod 755 /var/log/synolog


**Step 2 :** Create a script that will grant read access on the synobackup.log file

Create a script file, for example : **/volume1/scrips/chmod.sh**, with the following content

    #!/bin/sh
    chmod 664 /var/log/synolog/synobackup.log
    
Then, make it executable :

    chmod +x /volume1/scripts/chmod.sh
  
**Step 3 :** Schedule periodic execution of that script

In the Synology WEB interface, create a **scheduled task**, to run the custom script **/volume1/scrips/chmod.sh**. Schedule it every 5 minutes, from 00:00 to 23:55  


## How to check ? ##

Here's how to check manually if the plugin works :

Locally (on the Synology NAS console) :
 
    /opt/libexec/check_syno_backup.py -t "My Syno Backup Task Name" -W 30 -C 60

From the Nagios server console : 

    /usr/lib/nagios/plugins/check_nrpe -H <IP_OF_THE_SYNOLOGY_NAS> -p <MY_NRPE_PORT> -n -c syno_backup

For troubleshooting purposes, add the **-v** switch for more verbose output.


## Security considerations ##

For unknown reasons, I didn't manage to have NRPE work without the -nossl flag. 

This plugin is only intended to be used on an internal, secured network (VPN). 

I highly discourage exposing a bootstrapped Synology NAS server, with NRPE running in no-ssl mode, directly on Internet.


## Known problems ##

Here are some known problems and solutions :

- **"check permissions"** error in plugin output : check rights on directory **/etc/synolog** and on file **/etc/synolog/synobackup.log**. Check **chmod.sh** script, and corresponding scheduled task.
- **"nrpe : unable to read output"** on Nagios server : probable exception during plugin execution; run the plugin with the -v switch, and see what's going wrong 
- **"Error receiving data from daemon"** or **"Response packet had invalid CRC32"** on Nagios server : ensure you are running nrpe as a daemon (ie, not via xinetd); ensure the daemon is running in **nossl** mode (-n)

****
