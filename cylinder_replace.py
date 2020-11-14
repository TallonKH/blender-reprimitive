import bpy
import bmesh
from mathutils import Matrix
from . library import performOnSelectedIslands, fillHoles, projectOntoNormal
bops = bmesh.ops


class OBJECT__OT_cylinder_replace(bpy.types.Operator):
    bl_idname = "object.cylinderreplace"
    bl_label = "Cylinder Replace"
    bl_description = "Replaces existing cylinders with ones of specified segment count."
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {"REGISTER", "UNDO"}

    segment_count: bpy.props.IntProperty(
        name='Segment Count',
        default=12,
        min=3,
        soft_max=32,
        description="Number of segments in created cylinder.",)

    have_caps: bpy.props.EnumProperty(
        name='End Cap Generation',
        default='PRESERVE',
        items={('NEITHER', 'Neither', 'No caps.'), ('PRESERVE', 'Preserve',
                                                    'Only create caps where caps existed previously.'), ('BOTH', 'Both', 'Create caps on both ends.')},
        description="Whether end caps should be present or not.",)

    planar_spin: bpy.props.BoolProperty(
        name='Planar Spin',
        default=True,
        description="Adjust the spin of the faces to reduce non-planar faces.",)

    use_smooth_shading: bpy.props.BoolProperty(
        name='Smooth Shading',
        default=True,
        description="Render smooth.",)

    @classmethod
    def poll(cls, context):
        return (context.object != None) and context.object.select_get() and context.object.type == "MESH"

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        performOnSelectedIslands(context, self.logic, {
            "segment_count": self.segment_count,
            "have_caps": self.have_caps,
            "planar_spin": self.planar_spin,
            "use_smooth_shading": self.use_smooth_shading,
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

        self.createNewCylinder(bm, info, args)
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

            normal = end.normal
            infos.append({
                "center": center.copy(),
                "normal": normal.copy(),
                "rotation": normal.to_track_quat(),
                "minRadius": minRadius,
                "maxRadius": maxRadius,
                "avgRadius": radSum/count,
                "has_cap": cap,
            })

        bops.delete(bm, geom=ends, context="FACES_ONLY")

        return infos

    def createNewCylinder(self, bm, infos, args):
        if(len(infos) != 2):
            raise ValueError(
                "Cylinder not found! Are there exactly 2 faces with 3 or more than 4 faces?")

        segments = args["segment_count"]

        edges = []
        for info in infos:
            end_circ = bops.create_circle(bm,
                                          cap_ends=True,
                                          segments=segments,
                                          radius=info["avgRadius"])

            end_verts = end_circ["verts"]
            end_center = info["center"]
            bops.translate(bm, verts=end_verts, vec=end_center)
            bops.rotate(bm, verts=end_verts, cent=end_center,
                        matrix=info["rotation"].to_matrix())

            endFace = end_verts[0].link_faces[0]
            edges.extend(endFace.edges)
            info["face"] = endFace

        if(args["planar_spin"]):
            inf0 = infos[0]
            direction0 = inf0["face"].verts[0].co - inf0["center"]

            inf1 = infos[1]
            face1 = inf1["face"]
            direction1 = face1.verts[0].co - inf1["center"]
            norm1 = inf1["normal"].normalized()
            projDir = projectOntoNormal(direction0, norm1)
            angle = projDir.angle(direction1, 0)
            bops.rotate(bm, verts=face1.verts, cent=inf1["center"], matrix=Matrix.Rotation(
                angle, 4, norm1))

        bridges = bops.bridge_loops(bm, edges=edges)
        smooth = args["use_smooth_shading"]
        for face in bridges["faces"]:
            face.smooth = smooth

        capping = args["have_caps"]
        if(capping == "NEITHER"):
            bops.delete(bm, geom=[info["face"]
                                  for info in infos], context="FACES_ONLY")
        elif(capping == "PRESERVE"):
            bops.delete(bm, geom=[info["face"] for info in infos if (
                not info["has_cap"])], context="FACES_ONLY")
        elif(capping == "BOTH"):
            pass


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
        layout.prop(OBJECT__OT_cylinder_replace.planar_spin)
        layout.prop(OBJECT__OT_cylinder_replace.use_smooth_shading)
        props = layout.operator(OBJECT__OT_cylinder_replace.bl_idname)

        return {'FINISHED'}
