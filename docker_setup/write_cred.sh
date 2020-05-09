#!/bin/sh

touch /playbooks/cred.txt
touch foo.txt
echo $1 #>> /playbooks/cred.txt
echo $2 #>> /playbooks/cred.txt

echo $1 >> /playbooks/cred.txt
echo $2 >> /playbooks/cred.txt
