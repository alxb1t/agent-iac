COLL = ansible-galaxy collection install -r requirements.yml
apply:          ; $(COLL) && ansible-playbook alxb1t.agent_iac.apply -e box_file=$(CURDIR)/box.yaml
status:         ; ansible-playbook alxb1t.agent_iac.status -e box_file=$(CURDIR)/box.yaml
backup:         ; ansible-playbook alxb1t.agent_iac.backup -e box_file=$(CURDIR)/box.yaml
restore-drill:  ; ansible-playbook alxb1t.agent_iac.restore_drill -e box_file=$(CURDIR)/box.yaml
