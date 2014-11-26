faboto
======

# First Time Setup

git clone git@github.com:hailocab/faboto.git
cd faboto
sudo pip install virtualenv
source bin/activate
pip install

# Normal workflow

cd faboto
source bin/activate
fab ec2.ls

# Common Usage

```
fab -l                                      # lists the available tasks.
fab ec2.ls                                  # lists the hosts for the default region.
fab ec2.ls:,us-east-1                       # lists the hosts for a specific region.
fab ec2.ls:h2o                              # lists the hosts for the h2o role in the default region.
fab ec2.ls:h2o.h2o-raziel-lve               # lists the hosts for the h2o role and h2o-raziel-lve auto-scaling group in the default region.
fab ec2.run:h2o.h2o-raziel-lve psaux        # run ps aux on all of the h2o-raziel-lve hosts in the default region.
fab ec2.run:h2o.h2o-raziel-lve -- hostname  # run an adhoc command on all of the h2o-raziel-lve hosts.
fab hosts.eunsq cmd.pprof                   # run a pprof dump on the eunsq nodes one at a time.
```
