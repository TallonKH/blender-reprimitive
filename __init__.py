# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


if "bpy" in locals(): #means Blender already started once
    import importlib
    print("reload")
    importlib.reload(cylinder_replace)
else: #start up
    from . cylinder_replace import OBJECT__OT_cylinder_replace

import bpy

bl_info = {
    "name": "Reprimitive",
    "author": "TallonKH",
    "description": "Replaces existing primitives with new ones.",
    "blender": (2, 80, 0),
    "version": (1, 1, 0),
    "location": "View3D > Object",
    "warning": "",
    "category": "Object"
}

classes = (OBJECT__OT_cylinder_replace,)

register, unregister = bpy.utils.register_classes_factory(classes)