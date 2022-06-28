# Introduction

THis repository contains some NSDF libraries.
The structure of the directories is the following:

- `ansible/`. Contains all ansible rols to setup hosts and install software
- `nsdf/`
	- `catalog/`                   contains all the NSDF file catalog files.
	- `cloud/`                     contains the NSDF cloud source files (i.e. creating VM programmatcally) 
	- `kernel/`                    contains the basic code used by all other folders e.g. code to upload/download files from S3
	- `convert/`                   contains code OpenVisus specific to convert from/to other file formats
	- `distributed/`               contains code specific to Dask/Prefect to run tasks in parallel
	- `fuse/`                      contains the code specific to mount Object Storage as a file system. Compares several alternatives.
	- `material_science_workflow/` all the code specific to material science
	- `tamu/`                      all the code/scripts etc relative to Tamu collaboration

Please refer to each `ReadMe.md` file in each folder.


# Security checks before (!) commit

```
# trufflehog v2
sudo docker run --rm -v "$PWD:/pwd" dxa4481/trufflehog file:///pwd

# trufflehog v3
sudo docker run -it -v "$PWD:/pwd"  trufflesecurity/trufflehog:latest filesystem --directory=/pwd

# gitleaks
sudo docker run -v $PWD:/pwd zricethezav/gitleaks:latest detect -v --source="/pwd"

# git secrets `(`git clone https://github.com/awslabs/git-secrets && sudo make install`
git secrets --scan -r
git secrets --scan-history 



```