#!/usr/bin/expect -f
set account  [lindex $argv 0]
set from [lindex $argv 1]
set to [lindex $argv 2]
set timeout -1
spawn cyber link --from=$account --cid-from=$from --cid-to=$to --chain-id=bostrom
expect "* passphrase:"  {send -- "$env(CYBERD_PASS)\r"}
expect "* broadcasting *" {send -- "y\r"}
expect "* passphrase:"  {send -- "$env(CYBERD_PASS)\r"}

expect eof