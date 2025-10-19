# Jules-syslog_trap_processing
## sidecar for rsyslog and snmptrapd to simplify ticket creation

This project will create a process which listens on port 8514 and 8162 for syslog messages and traps. It will search the message for keywords that are included in ticket handling tables. If the keywords are matched, the program will consult the rest of the table for the ticket severity and the team assignment. It appends the new values to the message and formats all of the required datapoints to forward to a webhook which will create the actual tickets. 

I am going to try to use Jules to create this program with minimal direct coding. 
