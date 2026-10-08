"""cameras_188.py: street-level cameras on lafayette_188.blend (24 mm). Headless:
Blender --background build/lafayette_188.blend --python build/cameras_188.py"""
import bpy, math, os
from mathutils import Vector
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def cam(name, loc, target, lens=24):
    c = bpy.data.objects.get(name)
    if not c:
        c = bpy.data.objects.new(name, bpy.data.cameras.new(name)); bpy.context.scene.collection.objects.link(c)
    c.location = loc; c.data.lens = lens; c.data.clip_end = 2000
    c.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return c
# building corner (Broome x Lafayette) is at (11.5, 13.0); Lafayette centreline runs (-44.8,-96.5) -> (28.3,16.2) -> (64.9,72.9); Broome meets it at (28.3,16.2)
cam("CAM_188_corner", (38.0, 31.0, 1.65), (5.0, 2.0, 7.0))         # on Lafayette north of Broome, looking back at the corner
cam("CAM_188_lafayette", (17.7, -11.1, 1.65), (2.5, -1.1, 4.5))    # across Lafayette, facing the Parasol bays
cam("CAM_188_broome", (13.8, 24.3, 1.65), (8.4, 14.7, 3.0))        # on Broome, facing the pink Broome front
cam("CAM_188_broome_door", (12.7, 18.0, 1.6), (7.7, 15.1, 1.3))      # Broome sidewalk, angled at the inset Ceremonia door
sc = bpy.context.scene; sc.render.resolution_x = 1600; sc.render.resolution_y = 1000
# street renders: brighter overcast sky so the shaded facade reads (colours unchanged)
w = sc.world; bg = next((n for n in w.node_tree.nodes if n.type == "BACKGROUND"), None)
if bg: bg.inputs[0].default_value = (0.55, 0.56, 0.58, 1); bg.inputs[1].default_value = 2.2
# the corner faces north + east, so the dossier's south-west sun left it black. Street renders use a morning sun from the
# east-north-east (azimuth 70, elevation 32) that rakes both the Lafayette and Broome fronts, a brighter sky fill and +0.6 exposure.
sun = bpy.data.objects.get("SUN")
if sun:
    az, el = math.radians(70), math.radians(32)
    toward_sun = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
    sun.rotation_euler = (-toward_sun).to_track_quat('-Z', 'Y').to_euler(); sun.data.energy = 4.0
    try: sun.data.angle = math.radians(3)
    except Exception: pass
if bg: bg.inputs[1].default_value = 3.0
vs = sc.view_settings
looks = [i.identifier for i in type(vs).bl_rna.properties['view_transform'].enum_items]
for vt in ('AgX', 'Filmic', 'Standard'):
    if vt in looks:
        try: vs.view_transform = vt; break
        except TypeError: continue
vs.exposure = 0.6
# inside the corner shop (Ceremonia), looking out through the Lafayette and Broome glass. Local Lafayette-facade frame: x along, y out, z up.
root = bpy.data.objects.get("B188_LAFAYETTE")
if root:
    M = root.matrix_world
    cam("CAM_188_inside", tuple(M @ Vector((6.5, -5.6, 1.6))), tuple(M @ Vector((0.5, 1.5, 1.4))))
    cam("CAM_188_frontdoor", tuple(M @ Vector((0.9, -4.6, 1.6))), tuple(M @ Vector((11.0, -1.5, 1.2))))   # Broome front door, looking in
for n in ("CAM_188_frontdoor", "CAM_188_inside", "CAM_188_corner", "CAM_188_lafayette", "CAM_188_broome", "CAM_188_broome_door"):
    sc.camera = bpy.data.objects[n]; sc.render.filepath = os.path.join(OUT, "frames", n + ".jpg"); bpy.ops.render.render(write_still=True); print("rendered", n, flush=True)
bpy.ops.wm.save_mainfile(); print("SAVED", flush=True)
