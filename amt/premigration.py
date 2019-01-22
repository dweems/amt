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

from amt import migration, easyapache
import time

def disk_check(src, dest):
    if "G" in src.account_disk_usage and "G" in dest.avail_disk_space:
        if float(dest.avail_disk_space[:-1]) > float(src.account_disk_usage[:-1]):
            print("Disk space passed!")
            return True
    elif "M" in src.account_disk_usage and "G" in dest.avail_disk_space:
        if float(dest.avail_disk_space[:-1]*1024) > float(src.account_disk_usage[:-1]):
            print("Disk space passed!")
            return True
    elif "G" in src.account_disk_usage and "M" in dest.avail_disk_space:
        if float(dest.avail_disk_space[:-1]) > float(src.account_disk_usage[:-1]*1024):
            print("Disk space passed!")
            return True
    elif "M" in src.account_disk_usage and "M" in dest.avail_disk_space:
        if float(dest.avail_disk_space[:-1]) > float(src.account_disk_usage[:-1]):
            print("Disk space passed!")
            return True
    else:
        print("There does not appear to be enough disk space on the destination server.")
        return False

    print("There is not enough available disk space.")
    return False

def mysql_version_check(src, dest):
    if int(src.mysql_version.split(".")[0]) >= 5 and int(src.mysql_version.split(".")[1]) <=5 and "MariaDB" not in src.mysql_version:
        src.old_hash_accounts = src.run_command("mysql -t -e \"select distinct User,Password from mysql.user where Password not like '*%' and Password not like '-%' and Password not like '\!%';\" | awk '{print $2}' | grep -v User | grep [a-z] | tr \"\n\" \" \"")
        if src.old_hash_accounts is not "":
            print("The server is using an old hashing method, you'll need to reset the passwords for: {}".format(src.old_hash_accounts))
    if int(src.mysql_version.split(".")[0]) >= 5 and int(src.mysql_version.split(".")[1]) >= 6 or "MariaDB" in src.mysql_version and int(src.mysql_version.split(".")[1]) >= 1:
        print("MySQL passed!")
        return True
    
    print("MySQL version failure.")
    return False

def start(src, dest):
    print("Starting pre-migration check")
    
    while dest.run_command("ps uax | grep yum | grep -v grep")[2:-1] is not "":
        print("waiting for yum to finish")
        time.sleep(1)

    if disk_check(src, dest) is True and mysql_version_check(src, dest) is True and easyapache.check(src, dest) is True:
        print("Premigration check(s) passed!")
        return True