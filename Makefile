# The gate: the one list of the commands that say a change is done. Prose names
# `make gate` and never copies them. A new command lands through a change whose
# cut names this recipe in a task.
.PHONY: gate

# The playbooks resolve the collection's own FQCNs, so it is installed first; a syntax check
# needs none of its dependencies.
COLLECTIONS = .ansible/collections

gate:
	openspec validate --all --strict --no-interactive
	uv run yamllint .
	uv run ansible-lint
	export ANSIBLE_COLLECTIONS_PATH=$(COLLECTIONS) && uv run ansible-galaxy collection install --force --no-deps -p $(COLLECTIONS) . >/dev/null && uv run ansible-playbook --syntax-check playbooks/*.yml
	uv run pytest -q
