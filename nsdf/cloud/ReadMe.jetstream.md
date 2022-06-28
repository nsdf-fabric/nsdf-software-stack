# Jetstream setup

Links:

- https://jetstream2.exosphere.app/
- https://js2.jetstream-cloud.org
- https://iujetstream.atlassian.net/wiki/spaces/JWT/pages/641794049/Atmosphere+Command+Line+Interface?preview=%2F641794049%2F641859639%2Fimage2018-11-29_16-37-56.png
- https://github.com/eriksf/atmosphere-cli

## Prerequisites

Install Python packages

```
python3 -m pip install atmosphere-cli
```

## Generate ssh key

Generate an ssh key:

```
if [ ! -f ~/.ssh/id_nsdf ] ; then
  ssh-keygen -t rsa -f ~/.ssh/id_nsdf -N ""
fi
```

## Add ssh key

Go to https://use.jetstream-cloud.org/application/settings. On username click *Settings*, at the end of the page "*Show more*". 

Add a public SSH key:

- name: `id_nsdf`

## Generate Token

Add a new Personal Access Token

- Name: `id_nsdf`

## Examples

Create new nodes:

```
ACCOUNT=nsdf-cloud-jetstream-tacc
python3 -m nsdf.cloud $ACCOUNT create nodes test1 --num 3 --size-alias 
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

## Other useful commands

Setup the environment:

```
ATMO_BASE_URL=https://use.jetstream-cloud.or
ATMO_AUTH_TOKEN=XXXX
```

List ***instances**:

```
atmo instance list -f json
```

List  **allocations**:

```
atmo allocation source list -f json
```

List **images**:

```
atmo image list -f json
```

Search for **images**:

```
atmo image search ubuntu -f json
```

List of **identities**:

```
atmo  identity list -f json 
```

Show **sizes**:

```
atmo size list -f json
```

List **projects**:

```
atmo project list -f json
```

## All commands

```
Commands:
  allocation source list  List allocation sources for a user.
  allocation source show  Show details for an allocation source.
  complete                print bash completion command (cliff)
  group list              List groups for a user.
  group show              Show details for a group.
  help                    print detailed help for another command (cliff)
  identity list           List user identities managed by Atmosphere.
  identity show           Show details for a user identity.
  image list              List images for user.
  image search            Search images for user.
  image show              Show details for an image.
  image version list      List image versions for an image.
  image version show      Show details for an image version.
  instance actions        Show available actions for an instance.
  instance attach         Attach a volume to an instance.
  instance create         Create an instance.
  instance delete         Delete an instance.
  instance detach         Detach a volume from an instance.
  instance history        List history for instance.
  instance list           List instances for user.
  instance reboot         Reboot an instance.
  instance redeploy       Redeploy to an instance.
  instance resume         Resume an instance.
  instance shelve         Shelve an instance.
  instance show           Show details for an instance.
  instance start          Start an instance.
  instance stop           Stop an instance.
  instance suspend        Suspend an instance.
  instance unshelve        Unshelve an instance.
  maintenance record list  List maintenance records for Atmosphere.
  maintenance record show  Show details for a maintenance record.
  project create           Create a project.
  project list             List projects for a user.
  project show             Show details for a project.
  provider list            List cloud providers managed by Atmosphere.
  provider show            Show details for a cloud provider.
  size list                List sizes (instance configurations) for cloud provider.
  size show                Show details for a size (instance configuration).
  version                  Show Atmosphere API version.
  volume create            Create a volume.
  volume delete            Delete a volume.
  volume list              List volumes for a user.
  volume show              Show details for a volume.
```
