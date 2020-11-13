import bpy
import bmesh
from mathutils import Matrix

bops = bmesh.ops


# class CylinderReplaceProperties(bpy.types.PropertyGroup):
#     pass

class OBJECT__OT_cylinder_replace(bpy.types.Operator):
    bl_idname = "object.cylinderreplace"
    bl_label = "Cylinder Replace"
    bl_description = "Replaces existing cylinders with ones of specified segment count."
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {"REGISTER", "UNDO"}

    segment_count: bpy.props.IntProperty(
        name='segments',
        default=8,
        min=3,
        soft_max=24,
        description="Number of segments in created cylinder",)

    @classmethod
    def poll(cls, context):
        return context.object.select_get() and context.object.type == "MESH"

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        self.performOnSelected(context, self.logic, False, {
                               "segments": self.segment_count})
        return {'FINISHED'}

    def logic(self, bm, args):
        splitGeom = bops.split(
            bm, geom=[face for face in bm.faces if face.select])["geom"]

        for vert in bm.verts:
            vert.select = False
        for geom in splitGeom:
            geom.select = True

        info = self.extractInfo(bm)

        # check for validity because splitGeom will still contain the caps, which are already deleted by extractInfo
        bops.delete(
            bm, geom=list(g for g in splitGeom if g.is_valid), context="VERTS")

        self.createNewCylinder(bm, info, args["segments"])
        return True

    def extractInfo(self, bm):
        # delete existing caps
        caps = [face for face in bm.faces if (
            face.select and len(face.verts) != 4)]
        bops.delete(bm, geom=caps, context="FACES_ONLY")

        # create new caps (yes, this is redundant, but it works and doesn't disrupt selection stuff)
        ends = self.fillHoles(bm)['faces']

        infos = []

        # there are only ever 2 ends to iterate through
        for end in ends:
            normal = end.normal
            center = end.calc_center_median()

            minRadius = (center - end.verts[0].co).length
            maxRadius = minRadius
            radSum = 0
            count = len(end.verts)

            for vert in end.verts:
                rad = (center - vert.co).length
                radSum += rad

                if(rad < minRadius):
                    minRadius = rad

                if(rad > maxRadius):
                    maxRadius = rad
            infos.append({
                "center": center,
                "normal": normal,
                "rotation": normal.to_track_quat(),
                "minRadius": minRadius,
                "maxRadius": maxRadius,
                "avgRadius": radSum/count,
            })

        bops.delete(bm, geom=ends, context="FACES_ONLY")

        return infos

    def createNewCylinder(self, bm, infos, segments):
        if(len(infos) != 2):
            raise ValueError(
                "Cylinder not found! Are there exactly 2 faces with 3 or more than 4 faces?")

        inf1 = infos[0]
        inf2 = infos[1]

        circ1 = bops.create_circle(bm,
                                   cap_ends=True,
                                   segments=segments,
                                   radius=inf1["avgRadius"])
        circ2 = bops.create_circle(bm,
                                   cap_ends=True,
                                   segments=segments,
                                   radius=inf2["avgRadius"])

        verts1 = circ1["verts"]
        verts2 = circ2["verts"]
        bops.translate(bm, verts=verts1, vec=inf1["center"])
        bops.translate(bm, verts=verts2, vec=inf2["center"])
        bops.rotate(bm, verts=verts1,
                    cent=inf1["center"], matrix=inf1["rotation"].to_matrix())
        bops.rotate(bm, verts=verts2,
                    cent=inf2["center"], matrix=inf2["rotation"].to_matrix())
        end1 = verts1[0].link_faces[0]
        end2 = verts2[0].link_faces[0]
        bops.bridge_loops(bm, edges=list(end1.edges)+list(end2.edges))
        bops.delete(bm, geom=[end1], context="FACES_ONLY")
        bops.delete(bm, geom=[end2], context="FACES_ONLY")

    def fillHoles(self, bm, selectedOnly=True):
        return bops.contextual_create(bm, geom=[edge for edge in bm.edges if ((not selectedOnly) or edge.select) and edge.is_boundary])

    def performOnSelected(self, context, logic, discardChanges, args):
        print("run")
        mode = context.object.mode

        bm = None
        if(mode == 'EDIT'):
            ob = context.edit_object
            me = ob.data
            bm = bmesh.from_edit_mesh(me)
            success = logic(bm, args)
            if(success and (not discardChanges)):
                bmesh.update_edit_mesh(me)
        elif(mode == 'OBJECT'):
            for ob in context.selected_objects:
                me = ob.data
                bm = bmesh.new()
                bm.from_mesh(me)

                for vert in bm.verts:
                    vert.select = True
                for edge in bm.edges:
                    edge.select = True
                for face in bm.faces:
                    face.select = True
                success = logic(bm, args)
                if(success and (not discardChanges)):
                    bm.to_mesh(me)
                    me.update()
                bm.free()


class CylinderReplacePanel(bpy.types.Panel):
    bl_idname = "panel.cylinderreplace"
    bl_label = "Cylinder Replace"
    bl_category = "Cyldrop"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout

        layout.prop(OBJECT__OT_cylinder_replace.segment_count)
        props = layout.operator(OBJECT__OT_cylinder_replace.bl_idname)

        return {'FINISHED'}
