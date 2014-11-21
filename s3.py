from fabric.api import *
from boto import s3
from boto import connect_s3
from boto.s3.connection import Location

DEFAULT_REGION = 'eu-west-1'

@task
@runs_once
def ls(region_name=DEFAULT_REGION):
    """
    List all existing buckets.
    """
    s3conn = s3.connect_to_region(region_name)
    buckets = s3conn.get_all_buckets()
    for bucket in buckets:
        print(bucket.name)


@task
@runs_once
def add(bucket_name, permissions=None, region_name=Location.EU):
    """
    Add a bucket by name.
    """
    conn = connect_s3()
    conn.create_bucket(bucket_name, location=region_name)