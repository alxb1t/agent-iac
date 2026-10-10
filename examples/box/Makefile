COLL = ansible-galaxy collection install -r requirements.yml
apply:          ; $(COLL) && ansible-playbook alxb1t.agent_iac.apply -e box_file=$(CURDIR)/box.yaml
status:         ; ansible-playbook alxb1t.agent_iac.status -e box_file=$(CURDIR)/box.yaml
backup:         ; ansible-playbook alxb1t.agent_iac.backup -e box_file=$(CURDIR)/box.yaml
restore:        ; ansible-playbook alxb1t.agent_iac.restore -e box_file=$(CURDIR)/box.yaml
restore-drill:  ; ansible-playbook alxb1t.agent_iac.restore_drill -e box_file=$(CURDIR)/box.yaml
migrate:        ; $(if $(ZIP),,$(error usage: make migrate ZIP=<path to the zip>))$(if $(word 2,$(ZIP)),$(error ZIP=$(ZIP) has a space; rename the file or its folder)) ansible-playbook alxb1t.agent_iac.restore -e box_file=$(CURDIR)/box.yaml -e box_archive_file=$(abspath $(ZIP))
