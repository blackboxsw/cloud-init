# Copyright (C) 2012 Canonical Ltd.
#
# Author: Ben Howard <ben.howard@canonical.com>
#
# This file is part of cloud-init. See LICENSE file for license information.

"Users and Groups: Configure users and groups"

from textwrap import dedent

from cloudinit import log as logging
from cloudinit.config.schema import MetaSchema, get_meta_doc

# Ensure this is aliased to a name not 'distros'
# since the module attribute 'distros'
# is a list of distros that are supported, not a sub-module
from cloudinit.distros import ug_util
from cloudinit.settings import PER_INSTANCE

MODULE_DESCRIPTION = """\
This module configures users and groups. For more detailed information on user
options, see the :ref:`Including users and groups<yaml_examples>` config
example.

Groups to add to the system can be specified as a list under the ``groups``
key. Each entry in the list should either contain a the group name as a string,
or a dictionary with the group name as the key and a list of users who should
be members of the group as the value.

.. note::
   Groups are added before users, so any users in a group list must
   already exist on the system.

.. note::
    Specifying a hash of a user's password with ``passwd`` is a security risk
    if the cloud-config can be intercepted. SSH authentication is preferred.

.. note::
    If specifying a sudo rule for a user, ensure that the syntax for the rule
    is valid, as it is not checked by cloud-init.

.. note::
    Most of these configuration options will not be honored if the user
    already exists. The following options are the exceptions; they are applied
    to already-existing users: ``plain_text_passwd``, ``hashed_passwd``,
    ``lock_passwd``, ``sudo``, ``ssh_authorized_keys``, ``ssh_redirect_user``.
"""

meta: MetaSchema = {
    "id": "cc_users_groups",
    "name": "Users and Groups",
    "title": "Configure users and groups",
    "description": MODULE_DESCRIPTION,
    "distros": ["all"],
    "examples": [
        dedent(
            """\
        # Add the 'admingroup' with members 'root' and 'sys' and an empty
        # group cloud-users.
        groups:
        - admingroup: [root,sys]
        - cloud-users
        """
        ),
        dedent(
            """\
        # Skip creation of the <default> user and only create newsuper.
        # Password-based login is rejected, but the github user TheRealFalcon
        # and the launchpad user falcojr can SSH as newsuper. The default
        # shell for newsuper is bash instead of system default.
        users:
        - name: newsuper
          gecos: Big Stuff
          groups: users, admin
          sudo: ALL=(ALL) NOPASSWD:ALL
          shell: /bin/bash
          lock_passwd: true
          ssh_import_id:
            - lp:falcojr
            - gh:TheRealFalcon
        """
        ),
        dedent(
            """\
        # On a system with SELinux enabled, add youruser and set the
        # SELinux user to 'staff_u'. When omitted on SELinux, the system will
        # select the configured default SELinux user.
        users:
        - default
        - name: youruser
          selinux_user: staff_u
        """
        ),
        dedent(
            """\
        # To redirect a legacy username to the <default> user for a
        # distribution, ssh_redirect_user will accept an SSH connection and
        # emit a message telling the client to ssh as the <default> user.
        # SSH clients will get the message:
        users:
        - default
        - name: nosshlogins
          ssh_redirect_user: true
        """
        ),
    ],
    "frequency": PER_INSTANCE,
}

__doc__ = get_meta_doc(meta)

LOG = logging.getLogger(__name__)


def handle(name, cfg, cloud, _log, _args):
    (users, groups) = ug_util.normalize_users_groups(cfg, cloud.distro)
    (default_user, _user_config) = ug_util.extract_default(users)
    cloud_keys = cloud.get_public_ssh_keys() or []
    for (name, members) in groups.items():
        cloud.distro.create_group(name, members)
    for (user, config) in users.items():
        ssh_redirect_user = config.pop("ssh_redirect_user", False)
        if ssh_redirect_user:
            if "ssh_authorized_keys" in config or "ssh_import_id" in config:
                raise ValueError(
                    "Not creating user %s. ssh_redirect_user cannot be"
                    " provided with ssh_import_id or ssh_authorized_keys"
                    % user
                )
            if ssh_redirect_user not in (True, "default"):
                raise ValueError(
                    "Not creating user %s. Invalid value of"
                    " ssh_redirect_user: %s. Expected values: true, default"
                    " or false." % (user, ssh_redirect_user)
                )
            if default_user is None:
                LOG.warning(
                    "Ignoring ssh_redirect_user: %s for %s."
                    " No default_user defined."
                    " Perhaps missing cloud configuration users: "
                    " [default, ..].",
                    ssh_redirect_user,
                    user,
                )
            else:
                config["ssh_redirect_user"] = default_user
                config["cloud_public_ssh_keys"] = cloud_keys
        cloud.distro.create_user(user, **config)


# vi: ts=4 expandtab
