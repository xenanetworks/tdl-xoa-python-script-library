# ----- Import the Xena TCL Command Library ------
#
source [file dirname [info script]]/xena_api_main.tcl
source [file dirname [info script]]/xena_api_streams.tcl

# ----- Import the Test Globals ------
#
source [file dirname [info script]]/TestGlobals.tcl

# -------------------------------TEST MAIN-----------------------------------------
#
# --- Connect + Check Connected
set s [Connect $xena1_ip $xena1_port]

if {$s == "null"} {
	puts "Test Halted due to connection time out"
	return
} 
#

# --- Login and provide owner user-name
set response [Login $s $xena1_password $xena1_owner $console_flag]
# if {$response==0} { Validate Pass/Fail for Function reply}
#
# ------------------------------------------------------------------------------------

# --- Reserve ports
foreach port $ports {ReservePort $s $port $console_flag}

# ------------------------------------------------------------------------------------

# --- Stop Traffic+ClearResults+StartTraffic on all ports
foreach port $ports {StopPortTraffic $s $port $console_flag}


# --- Release all ports and disconnect
foreach port $ports { set response [release_port $s $port $console_flag] }
set response [Logout $s]
