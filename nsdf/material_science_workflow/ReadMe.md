# Instructions

Create and modify an Ansible `inventory.ini` file (see `./ansible/inventory.ini`)


Check the `./nsdf/material_science_workflow/workflow.yaml` file and **modify as needed**. 
For example you may need to change the `dask` section.

Export the workflow environment variables in the to your shell

```
export PYTHONPATH=$PWD
eval $(python3 -m nsdf.material_science_workflow export-env)
```

If the environment settings are right, you can now connect to the object storage:

```
BUCKET=Pania_2021Q3_in_situ_data
aws s3 --endpoint-url=${AWS_ENDPOINT_URL}  ls s3://$BUCKET
```

# Ping to your cluster

```
export INVENTORY=./ansible/inventory.ini
export GROUP=all
ansible -m ping --inventory ${INVENTORY} ${GROUP}
```

For DASK you may need to modify the `inventory.ini` to match the right `ansible_python_interpreter`

# (OPTIONAL) Check for disk:

```
ansible -m shell --inventory ${INVENTORY} -a "lsblk" ${GROUP}
ansible -m shell --inventory ${INVENTORY} -a "df -h" ${GROUP}
```

If you need to mount the disk:

```
DISK=/dev/nvme0n1 
MOUNT_DIR=/vol_b 
ansible-playbook --inventory ${INVENTORY} --limit ${GROUP} --extra-vars "disk=$DISK mount_dir=$MOUNT_DIR" ansible/mount-disk.yaml
```

# Preprocessing 


Setup the Virtual Machine for preprocessing (conda Python with NVidia GPU):

```
ansible-playbook --inventory ./ansible/inventory.ini --limit ${GROUP}  ansible/setup-conda.yaml

```

Check NVIDIA graphic card:

```
nvidia-smi
```

Modify `workflow.yaml` and modify the `num-process-per-host` to match the number of GPUs you have:


```
nvidia-smi --query-gpu=gpu_name
```


# OpenVisus convert


Setup the Virtual Machine for convert (CPython):

```
ansible-playbook --inventory ${INVENTORY} --limit ${GROUP}  ansible/setup-cpython.yaml
```


# (OPTIONAL) Fix clock issues 

```
dask_execute_code ntpdate -u in.pool.ntp.org
```

# (OPTIONAL) Firewalls/Security Groups

Check firewall status:

```
dask_execute_code sudo ufw status
```

In case of AWS EC2 machine make sure the *security group* allows incoming/outgoing connections for DASK.


# Run the workflow

```
# change inventory and group as needed
export INVENTORY=./ansible/inventory.ini
export GROUP=all

# assuming you are in the root of current repository
export PYTHONPATH=$PWD
eval $(python3 -m nsdf.material_science_workflow export-env)

# warm up clean the $LOCAL directory and sync the code with workers
dask_warm_up

python3 -m nsdf.material_science_workflow [--summarize] 
```

