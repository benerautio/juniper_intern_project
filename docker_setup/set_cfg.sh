#!/bin/sh

touch /etc/ansible/ansible.cfg

echo "[defaults]" >> /etc/ansible/ansible.cfg
echo "host_key_checking = False" >> /etc/ansible/ansible.cfg
