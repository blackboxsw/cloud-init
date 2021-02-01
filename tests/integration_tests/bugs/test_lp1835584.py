""" Integration test for LP #1835584

Kernels prior to 4.15 uppercased the dmi product_uuid, Azure
relies on system UUID as their "instance-id". Upgrades to kernels >= 4.15
will represent the same product_uuid as lowercase. System UUID should be a
case-insensitive comparison.

The test will launch an Ubuntu PRO FIPS image on Azure which has a 4.15 kernel.
It updates cloud-init on that instance and boots first into the 4.15 kernel.
Then install the linux-azure kernel which will install a 5.4 based kernel
which will boot by default because it's version is greater than 4.15.

Across the reboot, assert that we didn't re-run config_ssh by virtue of
seeing only one semaphore creation log entry of type:

 Writing to /var/lib/cloud/instances/<UUID>/sem/config_ssh -

https://bugs.launchpad.net/cloud-init/+bug/1897099
"""
import re

import pytest

from tests.integration_tests.clouds import IntegrationCloud


UBUNTU_PRO_FIPS_IMG = 'Canonical:0001-com-ubuntu-pro-bionic-fips:pro-fips-18_04'

def _check_iid_insensitive_across_kernel_upgrade(instance):
    uuid = instance.read_from_file('/sys/class/dmi/id/product_uuid')
    assert uuid.isupper(), "UUID does not appear to be upppercase {}".format(
      uuid
    )
    kernel = instance.read_from_file('uname -r').strip()
    assert kernel == '4.15.0-1002-azure-fips'
    if not instance.execute('sudo apt-get install linux-azure --assume-yes').ok:
        raise Exception("Failed installing linux-azure: {}".format(result))
    instance.restart()
    kernel = instance.execute('uname -r').strip()
    assert kernel == '5.4.0-1039-azure'
    uuid = instance.read_from_file('/sys/class/dmi/id/product_uuid')
    assert uuid.islower(), "UUID does not appear to be lowercase {}".format(
      uuid
    )
    log = instance.read_from_file('/var/log/cloud-init.log')
    RE_CONFIG_SSH_SEMAPHORE = r'Writing.*sem/config_ssh '
    matches = re.findall(RE_CONFIG_SSH_SEMAPHORE, log)
    assert 1 == len(matches), "config_ssh ran too many times {}".format(matches)


@pytest.mark.azure
@pytest.mark.sru_next
def test_upgrade_azure_uuid_case_insensitive(
    setup_image, session_cloud: IntegrationCloud
):
    try:
        with session_cloud.launch(launch_kwargs={
            'image_id': UBUNTU_PRO_FIPS_IMG
        }) as instance1:
            _check_iid_insensitive_across_kernel_upgrade(instance1)
    finally:
        session_cloud.cloud_instance.delete_image(snapshot_id)
        instance1.destroy()
