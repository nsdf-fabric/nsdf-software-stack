
## NSDF Cloud Examples

Create new nodes, for example on `nsdf-cloud-chameleon-tacc`:

```

# https://www.chameleoncloud.org/hardware/

# *************** UC ********************************
# gpu_rtx_6000          nc01            nc40           (NVIDIA)
# gpu_v100              P3-gpu-009      P3-gpu-012     (NVIDIA)
# compute_cascadelake_r P3-CPU-001      P3-CPU-042
# compute_skylake       nc41            nc63
# compute_nvdimm        P3-NVDIMM-001   P3-NVDIMM-002

# ***************TACC ********************************
# gpu_k80               c11-23          c11-24 (NVIDIA) 
# gpu_m40               c11-05          c11-06 (NVIDIA) 
# gpu_mi100             c02-01          c03-04 (AMD)
# gpu_p100              c11-07          c11-22 (NVIDIA) 
# gpu_p100_nvlink       c11-01          c11-04 (NVIDIA) 
# gpu_p100_v100         c11-14          c11-14 (NVIDIA) 
# compute_zen3          c02-05          c03-20
# compute_cascadelake_r c04-07          c07-20
# compute_cascadelake   c04-01          c07-04
# compute_skylake       c12-01          c12-32
# compute_haswell       c02-01          c03-42
# compute_haswell_ib    c01-01          c01-42
# storage               c02-43          c06-46
# storage_hierarchy     c10-21          c10-22
# compute_haswell       c04-01-retired  c05-08-retired
# fpga                  c10-27          c10-30

# compute_zen3 (CPU Mark 88,338)
# AMD AMD EPYC 7763 64-Core
# 256Gib
# 400GB-1TB

# compute_cascadelake_r (CPU Mark 56476)
# 2xIntel Xeon Gold 6240R CPU @ 2.40GHz
# 192 GiB
# 400GB-1TB

# compute_cascadelake  (CPU MARK 26,288)
# 2xIntel Xeon Gold 6242 CPU @ 2.80GHz
# 192 GiB
# 200-400GB

# 27 compute_skylake (CPU Mark 19,223)
# 2x Intel Xeon Gold 6126 CPU @ 2.60GHz
# 192GiB
# 200-400GB

# compute_haswell (CPU Mark 13,911)
# 2x Intel Xeon CPU E5-2670 v3 @ 2.30GHz
# 128 GiB
# 200-400GB

# compute_haswell_ib (CPU Mark 13,911)
# 2x Intel Xeon CPU E5-2670 v3 @ 2.30GHz
# 128 GiB
# 200-400GB

# compute_nvdimm
# 2x Intel Xeon Platinum 8276 CPU @ 2.20GHz
# 3792 GiB
# >1 TB

ACCOUNT=nsdf-cloud-chameleon-tacc
python3 -m nsdf.cloud $ACCOUNT create nodes nsdf-test  --num 10 --node-type compute_zen3

# ACCOUNT=nsdf-cloud-chameleon-uc
# python3 -m nsdf.cloud $ACCOUNT create nodes tamu-uc3 --num 3  --node-type gpu_rtx_6000
```

> You could get the *NOT_ENOUGH_RESOURCES* error message. Python code will retry to get the lease.

List of nodes:

```
python3 -m nsdf.cloud $ACCOUNT get nodes test1 
```

Delete nodes:

```
python3 -m nsdf.cloud $ACCOUNT delete nodes test1 
```

## Chameleon TACC

Instance types:

- compute_cascadelake
- compute_cascadelake_r
- **Haswell Infiniband nodes** compute_haswell_ib
- compute_nvdimm
- **Skylake compute nodes** compute_skylake
- compute_zen3
- **FPGA nodes** fpga
- **NVIDIA K80 nodes** gpu_k80
- **NVIDIA M40 nodes** gpu_m40
- gpu_mi100
- **NVIDIA P100 nodes** gpu_p100
- **NVIDIA P100 NVLink nodes** gpu_p100_nvlink
- gpu_p100_v100
- **Storage nodes** storage
- **Storage Hierarchy nodes** storage_hierarchy

## Chameleon UC

Instance types:

- compute_cascadelake_r
- compute_haswell
- **Skylake compute nodes** compute_skylake
- **FPGA nodes** fpga
- **NVIDIA RTX 6000 nodes** gpu_rtx_6000
- gpu_v100
- **Storage nodes** storage
- storage_nvme

# Chameleon setup

Links:

- [https://chi.uc.chameleoncloud.org/](https://chi.uc.chameleoncloud.org/)
- [https://chi.tacc.chameleoncloud.org](https://chi.tacc.chameleoncloud.org/)

Generate an ssh key:

```
if [ ! -f ~/.ssh/id_nsdf ] ; then
  ssh-keygen -t rsa -f ~/.ssh/id_nsdf -N ""
fi
```

 and import the public key to:

- https://chi.uc.chameleoncloud.org/project/key_pairs
- https://chi.tacc.chameleoncloud.org/project/key_pairs

with the folloing values:

- Key pair name: `id_nsdf`

- Key type: `SSH key`

- Public key: *paste the content of ~/.ssh/id_nsdf.pub*

## Update your vault file

Then add some items to your `~/.nsdf/vault/vault.yml` file (change values as needed; for example you may need to change `OS_PROJECT_ID`, `OS_PROJECT_NAME`, `OS_USERNAME`, `OS_PASSWORD`):

```
nsdf-cloud-chameleon-tacc:
  description: chameleon computing service
  resources: many Service Unit (SU)
  class: ChameleonEC2
  cloud-url: https://chi.tacc.chameleoncloud.org
  node-type: compute_haswell
  num: 1
  image-name: 'CC-Ubuntu20.04'
  network-name: 'sharednet1'
  lease-days: 7
  env:
    OS_AUTH_URL: https://chi.tacc.chameleoncloud.org:5000/v3
    OS_INTERFACE: public
    OS_PROTOCOL: openid
    OS_IDENTITY_PROVIDER: chameleon
    OS_DISCOVERY_ENDPOINT: https://auth.chameleoncloud.org/auth/realms/chameleon/.well-known/openid-configuration
    OS_CLIENT_ID: keystone-tacc-prod
    OS_ACCESS_TOKEN_TYPE: access_token
    OS_CLIENT_SECRET: none
    OS_REGION_NAME: CHI@TACC
    OS_PROJECT_DOMAIN_NAME: chameleon
    OS_AUTH_TYPE: v3oidcpassword
    OS_PROJECT_ID: 2c45428ad4584b52b336ba4ac62472fb
    OS_PROJECT_NAME: CHI-210923
    OS_USERNAME: XXXXX@YYYYY.edu
    OS_PASSWORD: ZZZZZ
  ssh-key-name: id_nsdf
  ssh-key-filename: ~/.ssh/id_nsdf
  ssh-username: cc

nsdf-cloud-chameleon-uc:
  class: ChameleonEC2
  node-type: compute_skylake
  num: 1
  image-name: 'CC-Ubuntu20.04'
  network-name: 'sharednet1'
  lease-days: 7
  env:
    OS_AUTH_URL: https://chi.uc.chameleoncloud.org:5000/v3
    OS_INTERFACE: public
    OS_PROTOCOL: openid
    OS_IDENTITY_PROVIDER: chameleon
    OS_DISCOVERY_ENDPOINT: https://auth.chameleoncloud.org/auth/realms/chameleon/.well-known/openid-configuration
    OS_CLIENT_ID: keystone-uc-prod
    OS_ACCESS_TOKEN_TYPE: access_token
    OS_CLIENT_SECRET: none
    OS_REGION_NAME: CHI@UC
    OS_PROJECT_DOMAIN_NAME: chameleon
    OS_AUTH_TYPE: v3oidcpassword
    OS_PROJECT_ID: 1b52ee31654449d589f010446827f89c
    OS_PROJECT_NAME: CHI-210923
    OS_USERNAME: XXXXX@YYYYY.edu
    OS_PASSWORD: ZZZZZZ
  ssh-key-name: id_nsdf
  ssh-key-filename: ~/.ssh/id_nsdf
  ssh-username: cc
```

Note: using *token credentials* does not work as confirmed by the Chameleon help center . The only work around is t use clear username/password that can be changed here [Log in to Chameleon](https://auth.chameleoncloud.org/auth/realms/chameleon/account/password) This seems to be related to some problems of the `python-chi` package.
