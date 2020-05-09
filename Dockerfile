FROM juniper/pyez-ansible

RUN apk update
RUN apk add expect

ENV host thunder-re0.ultralab.juniper.net
ENV username root
ENV password Juniper

#ARG host=10.85.162.142
#ARG username=root
#ARG password=lab123

COPY docker_setup/copyyodl /playbooks/copyyodl
COPY docker_setup/createyangpacks /playbooks/createyangpacks
COPY docker_setup/removejnpr /playbooks/removejnpr
COPY docker_setup/removeyaml /playbooks/removeyaml
COPY docker_setup/create_hosts.sh /playbooks/create_hosts.sh
COPY docker_setup/main.yaml /playbooks/main.yaml
COPY chip_agnostic_command_package/ /chip_agnostic_command_package
COPY docker_setup/main.exp /playbooks/main.exp
COPY docker_setup/set_cfg.sh /playbooks/set_cfg.sh
COPY docker_setup/write_cred.sh /playbooks/write_cred.sh
COPY docker_setup/test.sh /playbooks/test.sh

RUN sh test.sh

RUN export ANSIBLE_HOST_KEY_CHECKING=False

RUN sh /playbooks/create_hosts.sh ${host}
RUN sh /playbooks/set_cfg.sh

RUN sh /playbooks/write_cred.sh ${username} ${password}

RUN pip install --upgrade pip
RUN pip install --upgrade junos-eznc

CMD expect main.exp ${username} ${password}
