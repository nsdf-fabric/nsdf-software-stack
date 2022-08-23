from nsdf.kernel import RunCommand
import os


# ////////////////////////////////////////////////////////////////////////
def S3Sync(logger, name, src, dst):
	AWS_ENDPOINT_URL=os.environ["AWS_ENDPOINT_URL"]
	assert AWS_ENDPOINT_URL

	# is it a glob pattern e.g. /path/to/**/*.png
	if "/**/" in src:
		assert "/**/" in dst
		src_ext=os.path.splitext(src)[1];src=src.split("/**/")[0]
		dst_ext=os.path.splitext(dst)[1];dst=dst.split("/**/")[0]
		assert src_ext==dst_ext
		RunCommand(logger, name, f"aws s3 --endpoint-url={AWS_ENDPOINT_URL} sync --no-progress '{src}' '{dst}' --exclude '*' --include '*{src_ext}'")
	else:
		RunCommand(logger, name, f"aws s3 --endpoint-url={AWS_ENDPOINT_URL} sync --no-progress '{src}' '{dst}'")