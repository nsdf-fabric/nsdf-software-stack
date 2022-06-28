
import os,sys

# ////////////////////////////////////////////////////////////////
def LoadVault(filename="~/.nsdf/vault/vault.yaml"):
	from nsdf.kernel import LoadYaml
	return LoadYaml(os.path.expanduser(filename))

# ////////////////////////////////////////////////////////////////
def NormalizeEnv(env):
	ret={}
	for k,v in env.items():
		# possibility to include env from a vault account
		if k=="include-vault":
			accounts=v
			assert isinstance(accounts,tuple) or isinstance(accounts,list)
			from nsdf.kernel import LoadYaml
			vault=LoadVault()
			for account in accounts:
				ret={**ret, **NormalizeEnv(vault[account]["env"])}
		else:
			# safety check, only variable names with all capital letters
			assert k.upper()==k 
			ret[k]=v
	return ret

# ////////////////////////////////////////////////////////////////
def PrintEnv(env):
	for k,v in NormalizeEnv(env).items():
		print(f"export {k}={v}")

# ////////////////////////////////////////////////////////////////
def SetEnv(env):
	for k,v in env.items():
		os.environ[k]=v
