import bpy
import bmesh
from mathutils import Matrix
from . library import performOnSelectedIslands, fillHoles
bops = bmesh.ops


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

    have_caps: bpy.props.EnumProperty(
        name='caps',
        default='KEEP',
        items={('REMOVE', 'Remove', 'No caps.'), ('KEEP', 'Keep',
                                                  'Only create caps where caps existed previously.'), ('HAVE', 'Have', 'Create caps on both ends.')},
        description="Whether end caps should be present or not.",)

    @classmethod
    def poll(cls, context):
        return (context.object != None) and context.object.select_get() and context.object.type == "MESH"

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        performOnSelectedIslands(context, self.logic, {
            "segments": self.segment_count,
            "caps": self.have_caps,
        })
        return {'FINISHED'}

    def logic(self, context, bm, activeGeom, args):
        splitGeom = bops.split(
            bm, geom=list(activeGeom["faces"]), use_only_faces=True)["geom"]

        activeGeom = {
            "verts": [g for g in splitGeom if g.is_valid and isinstance(g, bmesh.types.BMVert)],
            "edges": [g for g in splitGeom if g.is_valid and isinstance(g, bmesh.types.BMEdge)],
            "faces": [g for g in splitGeom if g.is_valid and isinstance(g, bmesh.types.BMFace)],
        }
        info = self.extractInfo(bm, activeGeom)

        # check for validity because splitGeom will still contain the caps, which are already deleted by extractInfo
        bops.delete(bm, geom=activeGeom["verts"], context="VERTS")

        self.createNewCylinder(bm, info, args["segments"], args["caps"])
        return True

    def extractInfo(self, bm, activeGeom):
        # delete existing caps (and keep track of where they are)
        caps = [face for face in activeGeom["faces"] if len(face.verts) != 4]

        existingCap = None
        if len(caps) == 0:
            existingCap = "neither"
        elif len(caps) == 2:
            existingCap = "both"
        else:
            existingCap = caps[0].calc_center_median()

        bops.delete(bm, geom=caps, context="FACES_ONLY")

        # create new caps (yes, this is redundant, but it works and doesn't disrupt selection stuff)
        ends = fillHoles(bm, activeGeom["edges"])['faces']

        infos = []

        # there are only ever 2 ends to iterate through
        for end in ends:
            normal = end.normal
            center = end.calc_center_median()

            cap = False
            if(existingCap != "neither"):
                cap = (existingCap == "both") or (
                    (center - existingCap).length < 0.00001)

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
                "cap": cap,
            })

        bops.delete(bm, geom=ends, context="FACES_ONLY")

        return infos

    def createNewCylinder(self, bm, infos, segments, capping):
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
        if(capping != "HAVE"):
            if(capping == "REMOVE" or (not inf1["cap"])):
                bops.delete(bm, geom=[end1], context="FACES_ONLY")
            if(capping == "REMOVE" or (not inf2["cap"])):
                bops.delete(bm, geom=[end2], context="FACES_ONLY")


class CylinderReplacePanel(bpy.types.Panel):
    bl_idname = "panel.cylinderreplace"
    bl_label = "Cylinder Replace"
    bl_category = "Reprimitive"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout

        layout.prop(OBJECT__OT_cylinder_replace.segment_count)
        layout.prop(OBJECT__OT_cylinder_replace.have_caps)
        props = layout.operator(OBJECT__OT_cylinder_replace.bl_idname)

        return {'FINISHED'}
