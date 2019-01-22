# Automated Migration Tool
# Copyright (C) 2019 BronzeEagle

# This file is part of Automated Migration Tool.

# Automated Migration Tool is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Automated Migration Tool is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Automated Migration Tool.  If not, see <http://www.gnu.org/licenses/>.

from amt import premigration

def start(src, dest):
    if premigration.start(src, dest):
        print("Migration in progress")

        # # connect to source server and generate session_id
        # dest.session_id = dest.run_command("whmapi1 create_remote_root_transfer_session remote_server_type=cpanel host={} port={} user=root password={} transfer_threads=1 restore_threads=1 unrestricted_restore=1 copy_reseller_privs=0 compressed=0 unencrypted=0 low_priority=0 | grep -Po '(?<=(transfer_session_id: )).*'".format(src.hostname, src.port, src.password))[2:-3]
        
        # # Transfer all packages to dest server
        # if src.packages is not "":
        #     for package in src.packages.split(","):
        #         dest.run_command("whmapi1 enqueue_transfer_item transfer_session_id={} module=PackageRemoteRoot package={}".format(dest.session_id, package))

        # #loop through accounts and enqueue them
        # for account in src.accounts_split:
        #     dest.run_command("whmapi1 enqueue_transfer_item transfer_session_id={} module=AccountRemoteRoot localuser={} user={}".format(dest.session_id, account, account))
        
        # #when loop is done begin the transfer session
        # dest.run_command("whmapi1 start_transfer_session transfer_session_id={}".format(dest.session_id))
        
        print("Transfer Process has started!")
    print("Migration failed.")