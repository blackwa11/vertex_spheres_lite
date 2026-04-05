bl_info = {
    "name": "vertex_spheres_lite",
    "author": "blackwa11",
    "version": (1, 4),
    "blender": (3, 6, 0),
    "location": "View3D > N-panel > Vertex Lite",
    "description": "Create spheres hard-bound to mesh vertices",
    "category": "Object",
}

import bpy
import bmesh
from mathutils import Vector, Matrix

MAP_KEY = "vs_created_objects"


def _enter_mode(obj, mode):
    if bpy.context.active_object != obj:
        bpy.context.view_layer.objects.active = obj
    if obj.mode != mode:
        bpy.ops.object.mode_set(mode=mode)


def get_selected_vertex_indices(mesh_obj):
    bm = bmesh.from_edit_mesh(mesh_obj.data)
    bm.verts.ensure_lookup_table()
    return [v.index for v in bm.verts if v.select]


def get_all_vertex_indices(mesh_obj):
    return list(range(len(mesh_obj.data.vertices)))


def mesh_world_positions(mesh_obj):
    return [mesh_obj.matrix_world @ v.co for v in mesh_obj.data.vertices]


def hard_bind_to_vertex_exact(child, parent_mesh, world_target, v_index):
    child.parent = parent_mesh
    child.parent_type = 'VERTEX'
    child.parent_vertices = [int(v_index), int(v_index), int(v_index)]
    child.matrix_parent_inverse = Matrix.Identity(4)
    bpy.context.view_layer.update()

    mw = parent_mesh.matrix_world
    mw_inv = mw.inverted()
    v_local = parent_mesh.data.vertices[v_index].co.copy()
    desired_local = mw_inv @ world_target
    local_delta = desired_local - v_local

    if local_delta.length <= 1e-8:
        child.location = Vector((0.0, 0.0, 0.0))
    else:
        child.location = local_delta

    child.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()


class VSProps(bpy.types.PropertyGroup):
    size: bpy.props.FloatProperty(
        name="Sphere Size",
        default=0.08,
        min=0.0001
    )
    use_all_if_none: bpy.props.BoolProperty(
        name="If none selected → use all verts",
        default=True
    )


class VS_OT_create(bpy.types.Operator):
    bl_idname = "vs.create"
    bl_label = "Create Spheres"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        src = context.active_object

        if not src or src.type != 'MESH':
            self.report({'ERROR'}, "Active object must be a mesh")
            return {'CANCELLED'}

        props = context.scene.vs_props
        prev_mode = src.mode

        if src.mode == 'EDIT':
            indices = get_selected_vertex_indices(src)
        else:
            indices = []

        if not indices and props.use_all_if_none:
            indices = get_all_vertex_indices(src)

        if not indices:
            self.report({'ERROR'}, "No vertices selected")
            return {'CANCELLED'}

        _enter_mode(src, 'OBJECT')
        positions = mesh_world_positions(src)

        created_names = []
        for vid in indices:
            world_pos = positions[vid]
            bpy.ops.mesh.primitive_uv_sphere_add(radius=props.size, location=world_pos)
            child = bpy.context.active_object
            hard_bind_to_vertex_exact(child, src, world_pos, vid)
            created_names.append(child.name)

        src[MAP_KEY] = created_names
        _enter_mode(src, prev_mode)

        self.report({'INFO'}, f"Created {len(created_names)} bound sphere(s)")
        return {'FINISHED'}


class VS_OT_delete_created(bpy.types.Operator):
    bl_idname = "vs.delete_created"
    bl_label = "Delete Created"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        src = context.active_object

        if not src or src.type != 'MESH':
            self.report({'ERROR'}, "Select the source mesh object")
            return {'CANCELLED'}

        names = list(src.get(MAP_KEY, []))
        removed = 0

        for name in names:
            ob = bpy.data.objects.get(name)
            if ob:
                bpy.data.objects.remove(ob, do_unlink=True)
                removed += 1

        if MAP_KEY in src:
            del src[MAP_KEY]

        self.report({'INFO'}, f"Deleted {removed} sphere(s)")
        return {'FINISHED'}


class VS_PT_panel(bpy.types.Panel):
    bl_label = "Vertex Spheres Lite"
    bl_idname = "VS_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Vertex Lite'

    def draw(self, context):
        layout = self.layout
        props = context.scene.vs_props

        layout.prop(props, "size")
        layout.prop(props, "use_all_if_none")
        layout.operator("vs.create")
        layout.operator("vs.delete_created", icon='TRASH')


classes = (
    VSProps,
    VS_OT_create,
    VS_OT_delete_created,
    VS_PT_panel,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.vs_props = bpy.props.PointerProperty(type=VSProps)


def unregister():
    del bpy.types.Scene.vs_props
    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
