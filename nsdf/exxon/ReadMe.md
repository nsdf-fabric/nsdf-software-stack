
# IMPORTANT

**SECRED EXPOSED, do not share**

# Node setup

```
export INVENTORY=./ansible/inventory.ini
export GROUP=chameleon
ansible -m ping --inventory ${INVENTORY} ${GROUP}
ansible -m shell --inventory ${INVENTORY} -a "df -h" ${GROUP}
ansible-playbook --inventory ${INVENTORY} --limit ${GROUP}  ansible/setup-cpython.yaml


# make sure you have `~/.aws/config` and `/.aws/credentials` with propert wasabi credentials
```

For running, see `run.sh`.
For testing, see `test-time.ipynb`.