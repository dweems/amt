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

from amt import Source, Server, migration

source = Source("root", "ipaddress", "password", 2200, "list of accounts separated by spaces")
destination = Server("root", "ipaddress", "password", 2200)

migration.start(source, destination)