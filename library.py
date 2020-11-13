import bpy
import bmesh

bops = bmesh.ops

# logic : function(bpy.context, bmesh object, {verts:[], edges:[], faces:[]}, args)

def performOnSelected(context, logic, args):
    mode = context.object.mode

    bm = None
    if(mode == 'EDIT'):
        ob = context.edit_object
        me = ob.data
        bm = bmesh.from_edit_mesh(me)

        activeGeom = {
            'verts': set(vert for vert in bm.verts if vert.select),
            'edges': set(edge for edge in bm.edges if edge.select),
            'faces': set(face for face in bm.faces if face.select),
        }
        success = logic(context, bm, activeGeom, args)

        if(success):
            bmesh.update_edit_mesh(me)
    elif(mode == 'OBJECT'):
        for ob in context.selected_objects:
            me = ob.data
            bm = bmesh.new()
            bm.from_mesh(me)

            activeGeom = {
                'verts': set(vert for vert in bm.verts),
                'edges': set(edge for edge in bm.edges),
                'faces': set(face for face in bm.faces),
            }
            success = logic(context, bm, activeGeom, args)
            if(success):
                bm.to_mesh(me)
                me.update()
                bm.free()
            bm.free()


def edgesFromVerts(vertSet):
    edges = set()
    for vert in vertSet:
        for edge in vert.link_edges:
            if(edge in edges):
                continue
            if(all((v in vertSet) for v in edge.verts)):
                edges.add(edge)
    return edges


def facesFromVerts(vertSet):
    faces = set()
    for vert in vertSet:
        for face in vert.link_faces:
            if(face in faces):
                continue
            if(all((v in vertSet) for v in face.verts)):
                faces.add(face)
    return faces


def performOnIslands(context, bm, activeGeom, logic, args):
    for island in get_islands(bm, activeGeom["verts"]):
        islandGeom = {
            "verts": island,
            "edges": edgesFromVerts(island),
            "faces": facesFromVerts(island),
        }
        print(str(len(islandGeom["faces"])) + " faces in island")
        success = logic(context, bm, islandGeom, args)
        if(not success):
            return False
    return True


def performOnSelectedIslands(context, logic, args):
    return performOnSelected(context,
                      (lambda ctx, bm, geom, args2: performOnIslands(
                          ctx, bm, geom, logic, args2)
                       ), args)


def walk_island(vert):  # https://blender.stackexchange.com/a/105142
    vert.tag = True
    yield(vert)
    linked_verts = [e.other_vert(vert) for e in vert.link_edges
                    if not e.other_vert(vert).tag]

    for v in linked_verts:
        if v.tag:
            continue
        yield from walk_island(v)


def get_islands(bm, verts=[]):  # https://blender.stackexchange.com/a/105142
    def tag(verts, switch):
        for v in verts:
            v.tag = switch
    tag(bm.verts, True)
    tag(verts, False)
    ret = []
    verts = set(verts)
    while verts:
        v = verts.pop()
        verts.add(v)
        island = set(walk_island(v))
        ret.append(list(island))
        tag(island, False)  # remove tag = True
        verts -= island
    return ret

def fillHoles(bm, consideredEdges):
    return bops.contextual_create(bm, geom=[edge for edge in consideredEdges if edge.is_boundary])