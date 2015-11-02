# euphoria-py
# Copyright (C) 2015  Emily A. Bellows
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Euphoria client and bot library, for Python 3.5"""

# noinspection PyUnresolvedReferences
from .exceptions import *
# noinspection PyUnresolvedReferences
from .data import *
# noinspection PyUnresolvedReferences
from .client import *
# noinspection PyUnresolvedReferences
from .state_machines import *
# noinspection PyUnresolvedReferences
from .bot import *

__all__ = (exceptions.__all__ +
           data.__all__ +
           client.__all__ +
           state_machines.__all__ +
           bot.__all__)
