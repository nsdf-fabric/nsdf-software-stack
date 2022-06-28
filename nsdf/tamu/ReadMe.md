# Tamu collaboration

Links:
- https://console.wasabisys.com/#/file_manager/nsdf-tamu
- https://github.com/nsdf-fabric/nsdf-tamu

## Workflow

 ![TAMU WORKFLOW](https://github.com/nsdf-fabric/nsdf-tamu/raw/main/assets/workflow.png)


- Input file EER
  - Each file about 1.68GiB 
  - https://guide.cryosparc.com/processing-data/tutorials-and-case-studies/tutorial-eer-file-support

- Align the images
   - **UCSD EM Core** https://emcore.ucsf.edu/ucsf-software 

- Preprocessing
  - **EMAN2** - https://blake.bcm.edu/emanwiki/EMAN2
  - **BSOFT**  bsoft.ws

- Reconstruction (the most time consuming step)
  - **CryoSPARC** - https://cryosparc.com 
  - **RELION**  https://relion.readthedocs.io
  - **cisTEM**  https://cistem.org
  
- Visualization
  - *UCSF Chimera* - https://www.cgl.ucsf.edu/chimera

## Python scripts

```

# list all files in the bucket
python3 main.py
```


## Uploading data to Wasabi


On Linux/MacOs

```
sudo apt-get update

python3 -m pip install --upgrade awscli
source $(python3 -m nsdf export-env s3-tamu)
export BUCKET=nsdf-tamu

aws configure set default.s3.max_concurrent_requests 300
aws s3 ls --endpoint-url=${AWS_ENDPOINT_URL} s3://${BUCKET}

# change directory as needed
aws s3 sync  --endpoint-url=${AWS_ENDPOINT_URL} /your/local/dir/here s3://${BUCKET}
```
