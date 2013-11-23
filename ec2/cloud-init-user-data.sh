#!/bin/sh -x

# This script is intended to be fed as user data to an EC2 spot instance request.
# Whenever a new spot instance is created, the instance will execute this script
# once (on first boot) via cloud-init.

# update packages to lates
yum update -y

# install prereqs and make boto available to python2.7
yum install -y R-core python27 python-boto aws-apitools-ec2 ec2-utils rsync
ln -s /usr/lib/python2.6/site-packages/boto/ /usr/lib/python2.7/site-packages/

# set up aws-apitools now that it's installed
. /etc/profile.d/aws-apitools-common.sh

# locate an unattached EBS volume in the same availability zone that has a Purpose=RedFrogDisk tag
# this will eventually end up mounted under /rf and should have the scraper installation
REGION=eu-west-1
ZONE=`ec2-metadata -z | cut -d\  -f2`
INSTANCEID=`ec2-metadata -i | cut -d\  -f2`
VOLID=`ec2-describe-volumes --region $REGION --filter "availability-zone=$ZONE" --filter "tag:Purpose=RedFrogDisk" --filter "status=available" | grep ^VOLUME | cut -f2`

# attach to the EBS volume and wait for attachment to complete
ec2-attach-volume --region $REGION $VOLID -i $INSTANCEID -d /dev/sdb1
while [ ! -e /dev/sdb1 ]
do
  echo "Waiting for disk to appear.."
  sleep 30
done

# mount it
mkdir /rf
chown ec2-user:ec2-user /rf

# ensure it is remounted on reboot
cat >>/etc/fstab <<EOF
/dev/sdb1 /rf ext4 defaults 1 1
EOF

# update rc.local to run the updater
cat >>/etc/rc.local <<EOF
su ec2-user -c "cd /rf; nohup ./updater.py >>log/updater.log 2>&1 &"
EOF

# reboot the instance so that we've picked up all changes
reboot
