import bpy
import bmesh

def performOnSelected(context, logic, discardChanges, args):
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