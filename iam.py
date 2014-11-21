from fabric.api import *
from boto.iam import connect_to_region, regions

DEFAULT_REGION = 'universal'
ADMIN_GROUP = 'admin'

# TODO: (NF 2013-02-04) Handle connection exceptions.

@task
def add(user_name, region_name=DEFAULT_REGION):
    """Add the given user name as an admin and output their access keys.

    Keyword arguments:
    user_name -- User name to add.
    region_name -- Region to connect to.

    """
    password = prompt('Please enter a temporary password:')
    conn = connect_to_region(region_name)
    conn.create_user(user_name)
    conn.add_user_to_group(ADMIN_GROUP, user_name)
    conn.create_login_profile(user_name, password)
    key_response = conn.create_access_key(user_name)
    print(key_response.access_key_id)
    print(key_response.secret_access_key)


@task
def rm(user_name, region_name=DEFAULT_REGION):
    """Remove the given user name and their access keys.

    Keyword arguments:
    user_name -- User name to remove.
    region_name -- Region to connect to.
    
    """
    conn = connect_to_region(region_name)
    conn.remove_user_from_group(ADMIN_GROUP, user_name)
    access_keys = conn.get_all_access_keys(user_name).access_key_metadata
    for access_key in access_keys:
        conn.delete_access_key(access_key.access_key_id, user_name)
    conn.delete_login_profile(user_name)
    conn.delete_user(user_name)


@task
def ls(region_name=DEFAULT_REGION):
    """List all users.

    Keyword arguments:
    region_name -- Region to connect to.

    """
    conn = connect_to_region(region_name)
    users = conn.get_all_users().users
    for user in users:
        print(user.user_name)