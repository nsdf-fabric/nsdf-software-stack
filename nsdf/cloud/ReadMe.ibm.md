# IBM Cloud setup

Links:

- https://www.ibm.com/cloud/cli
- https://cloud.ibm.com/docs/cli?topic=cli-getting-started
- https://github.com/IBM-Cloud/ibm-cloud-cli-release/issues/57
- https://cloud.ibm.com/docs/vpc?topic=vpc-infrastructure-cli-plugin-vpc-reference
- https://github.com/IBM/vpc-python-sdk


TODO...

### Prerequisites

https://github.com/IBM/vpc-python-sdk


### Credential Setup up in Vendor IAM & SSH Keys

```
pip install --upgrade "ibm-vpc>=0.10.0"
```



## NSDF-Cloud Example: Create, List, Delete

Create new nodes:

```
ACCOUNT=TODO
python3 -m nsdf.cloud $ACCOUNT create nodes test1 --num 1 
```

List of nodes:

```
python3 -m nsdf.cloud $ACCOUNT get nodes test1 

# to get all nodes remove `test1`
```

Delete nodes:

```
python3 -m nsdf.cloud $ACCOUNT delete nodes test1 

# to delete all nodes remove `test1`
```



### Other Useful with Vendor Tools

Consider installing IBM Cloud CLI from https://www.ibm.com/cloud/cli for your system.

```
ibmcloud login
```

```
ibmcloud plugin install vpc-infrastructure
```

The "vpc-infrastructure" plugin adds the is subcommand which allows to control VPC resources.

E.g., to list instances use:
```
ibmcloud si instances
