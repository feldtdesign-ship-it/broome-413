"""
build_188.py
Block model for 188 Lafayette St (Parasol unit, Sing Tao building, 413 Broome) from NYC Open Data layers on disk (data/planimetric).
Same build as mott-167/build/build_mott.py, pointed at this site, with stage_building() for the Sing Tao building.
Headless: /Applications/Blender.app/Contents/MacOS/Blender --background --python build/build_188.py
"""
import bpy, bmesh, json, math, os, sys
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

OUT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if '__file__' in globals() else "/Users/michaelweinfeld/Documents/2026/PJ O'Rourke/Location Research/lafayette-188"
DATA_DIR = os.path.join(OUT_DIR, "data", "planimetric")
SITE_LAT, SITE_LON = 40.7209251, -73.9985317
SITES = {"1004730040": ("SITE_188_LAF", "PJ_TAN")}
FT = 0.3048; H_FALLBACK = 9.0; COLLECTION = "LAF_188"
# dark ground; Sing Tao building in its tan brick, the painted pink base as it stands, PJ's Parasol bays framed in 6-train green (Spring St, 192 m). Colours are one line to change.
PALETTE = {"PJ_INK": "2A2724", "PJ_GROUND": "141210", "PJ_ROAD": "1C1A18", "PJ_WALK": "2B2823", "PJ_MEDIAN": "34302A", "PJ_TREE": "4A5A3A", "PJ_BRICK": "8A5A46", "PJ_SITE": "00933C", "PJ_GLASS": "0D1714", "PJ_TRIM": "C9C2B4", "PJ_IRON": "121212", "PJ_SHED": "2F5D3A", "PJ_LABEL": "8A857C", "PJ_TAN": "B89B72", "PJ_PINK": "D9608F", "PJ_SIGN": "E9E6DF", "PJ_COBRA": "D9A21B", "PJ_TIGER": "7A5A9A", "PJ_RED": "B3262D", "PJ_SHOPGLASS": "A9B8B4", "PJ_FLOOR": "8C8A86", "PJ_WHITE": "E8E5DE", "PJ_WOOD": "5A3E2B", "PJ_PLASTER": "D8C7AE"}
COSL = math.cos(math.radians(SITE_LAT))

def proj(lon, lat): return ((lon - SITE_LON) * 111320.0 * COSL, (lat - SITE_LAT) * 110540.0)
def hex_to_linear(h):
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i+2], 16) / 255.0; out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (out[0], out[1], out[2], 1.0)
def make_materials():
    for name, hexc in PALETTE.items():
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes = True
        b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if b: b.inputs["Base Color"].default_value = hex_to_linear(hexc); b.inputs["Roughness"].default_value = 0.95
        m.diffuse_color = hex_to_linear(hexc)
        if name == "PJ_SHOPGLASS" and b:                                                      # clear storefront glass
            b.inputs["Alpha"].default_value = 0.10; b.inputs["Roughness"].default_value = 0.04
            for k in ("Specular IOR Level", "Specular"):                                      # no reflection: EEVEE mirrored the pink wall into it
                if k in b.inputs: b.inputs[k].default_value = 0.0
            for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND"), ("use_backface_culling", False), ("show_transparent_back", True), ("use_transparency_overlap", True)):
                try: setattr(m, attr, val)
                except Exception: pass
def load(key): return json.load(open(os.path.join(DATA_DIR, key + ".geojson")))["features"]
def rings(geom):
    t = geom.get("type"); c = geom.get("coordinates", [])
    if t == "Polygon": return [c[0]] if c else []
    if t == "MultiPolygon": return [p[0] for p in c if p]
    return []
def contours(geom):
    t = geom.get("type"); c = geom.get("coordinates", [])
    src = [c] if t == "Polygon" else (c if t == "MultiPolygon" else [])
    for poly in src:
        out = []
        for ring in poly:
            pts = [proj(a, b) for a, b in ring]; cl = []
            for p in pts:
                if not cl or abs(p[0]-cl[-1][0]) > 1e-7 or abs(p[1]-cl[-1][1]) > 1e-7: cl.append(p)
            if len(cl) > 2 and abs(cl[0][0]-cl[-1][0]) < 1e-7 and abs(cl[0][1]-cl[-1][1]) < 1e-7: cl = cl[:-1]
            if len(cl) >= 3: out.append(cl)
        if out: yield out
def get_collection():
    old = bpy.data.collections.get(COLLECTION)
    if old:
        for o in list(old.objects): bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(old)
    col = bpy.data.collections.new(COLLECTION); bpy.context.scene.collection.children.link(col); return col
def col(): return bpy.data.collections.get(COLLECTION) or get_collection()

def extrude_ring(bm, xy, z0, z1):
    cl = []
    for p in xy:
        if not cl or abs(p[0]-cl[-1][0]) > 1e-6 or abs(p[1]-cl[-1][1]) > 1e-6: cl.append(p)
    if len(cl) > 2 and abs(cl[0][0]-cl[-1][0]) < 1e-6 and abs(cl[0][1]-cl[-1][1]) < 1e-6: cl = cl[:-1]
    if len(cl) < 3: return False
    vs = [bm.verts.new((p[0], p[1], z0)) for p in cl]
    try: face = bm.faces.new(vs)
    except ValueError: return False
    res = bmesh.ops.extrude_face_region(bm, geom=[face])
    bmesh.ops.translate(bm, vec=(0, 0, z1 - z0), verts=[v for v in res["geom"] if isinstance(v, bmesh.types.BMVert)])
    return True

def stage_massing():
    make_materials(); c = get_collection(); feats = load("footprints")
    bases = [float(f["properties"].get("ground_elevation") or 0) for f in feats if f["properties"].get("base_bbl") in SITES]
    base = sum(bases) / len(bases) if bases else 0.0
    bm = bmesh.new(); sbms = {k: bmesh.new() for k in SITES}; n = 0; guessed = 0
    for f in feats:
        p = f["properties"]
        try: h_ft = float(p.get("height_roof") or 0)
        except ValueError: h_ft = 0.0
        h = h_ft * FT
        if h <= 0: h = H_FALLBACK; guessed += 1
        ge = (float(p.get("ground_elevation") or base) - base) * FT
        target = sbms.get(p.get("base_bbl"), bm)
        for ring in rings(f["geometry"]):
            if extrude_ring(target, [proj(a, b) for a, b in ring], ge, ge + h): n += 1
    for b, name, mat in [(bm, "SOHO_MASSING", "PJ_INK")] + [(sbms[k], SITES[k][0], SITES[k][1]) for k in SITES]:
        bmesh.ops.recalc_face_normals(b, faces=b.faces); me = bpy.data.meshes.new(name); b.to_mesh(me); b.free()
        ob = bpy.data.objects.new(name, me); c.objects.link(ob); ob.data.materials.append(bpy.data.materials[mat])
    return "massing: {} solids, {} without height".format(n, guessed)

def build_flat(key, name, z, mat):
    feats = load(key); verts, faces = [], []
    for f in feats:
        for cont in contours(f["geometry"]):
            vecs = [[Vector((x, y, 0.0)) for (x, y) in ring] for ring in cont]; flat = [v for ring in vecs for v in ring]; b = len(verts)
            try: idx = tessellate_polygon(vecs)
            except Exception: continue
            verts.extend([(v.x, v.y, z) for v in flat]); faces.extend([(b+t[0], b+t[1], b+t[2]) for t in idx])
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    ob = bpy.data.objects.new(name, me); col().objects.link(ob); ob.data.materials.append(bpy.data.materials[mat])
    return "{}: {} tris".format(name, len(faces))
def stage_flat():
    return "; ".join([build_flat("roadbed", "ROADBED", 0.02, "PJ_ROAD"), build_flat("sidewalk", "SIDEWALK", 0.14, "PJ_WALK"), build_flat("median", "MEDIAN", 0.18, "PJ_MEDIAN")])

def at_fraction(pts, frac):
    segs = [math.dist(pts[i], pts[i+1]) for i in range(len(pts)-1)]; total = sum(segs); want = total * frac; run = 0.0
    for i, s in enumerate(segs):
        if run + s >= want:
            t = (want - run) / s if s else 0.0; a, b = pts[i], pts[i+1]
            return ((a[0] + (b[0]-a[0])*t, a[1] + (b[1]-a[1])*t), math.atan2(b[1]-a[1], b[0]-a[0]))
        run += s
    return pts[-1], math.atan2(pts[-1][1]-pts[0][1], pts[-1][0]-pts[0][0])
def stage_labels(size=12.0, min_gap=34.0):
    feats = load("centerline"); longest = {}
    for f in feats:
        n = (f["properties"].get("stname_label") or "").strip()
        if not n: continue
        g = f["geometry"]; parts = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
        for line in parts:
            pts = [proj(a, b) for a, b in line]; L = sum(math.dist(pts[i], pts[i+1]) for i in range(len(pts)-1))
            if n not in longest or L > longest[n][0]: longest[n] = (L, pts)
    placed = []
    for name, (L, pts) in sorted(longest.items(), key=lambda kv: -kv[1][0]):
        if L < 40: continue
        spot = None
        for frac in (0.5, 0.3, 0.7, 0.18, 0.82):
            p, ang = at_fraction(pts, frac)
            if all(math.dist(p, q) > min_gap for q in placed): spot = (p, ang); break
        if spot is None: spot = at_fraction(pts, 0.5)
        p, ang = spot
        if ang > math.pi/2: ang -= math.pi
        if ang < -math.pi/2: ang += math.pi
        cu = bpy.data.curves.new("ST_" + name, type='FONT'); cu.body = name; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.size = size; cu.extrude = 0.04; cu.space_character = 1.15
        ob = bpy.data.objects.new("ST_" + name, cu); col().objects.link(ob); ob.location = (p[0], p[1], 0.6); ob.rotation_euler = (0, 0, ang); ob.data.materials.append(bpy.data.materials["PJ_LABEL"]); placed.append(p)
    return "labels: {}".format(len(placed))

def stage_trees():
    rows = [r for r in json.load(open(os.path.join(DATA_DIR, "trees.json"))) if r.get("status") == "Alive"]
    bm = bmesh.new(); n = 0
    for t in rows:
        try: x, y = proj(float(t["longitude"]), float(t["latitude"])); dbh = float(t.get("tree_dbh") or 6)
        except (TypeError, ValueError, KeyError): continue
        r = max(1.4, min(4.2, 1.2 + dbh * 0.12)); h = max(4.0, min(11.0, 3.5 + dbh * 0.35))
        tb = bmesh.new(); bmesh.ops.create_icosphere(tb, subdivisions=1, radius=1.0); bmesh.ops.scale(tb, vec=(r, r, r * 0.8), verts=tb.verts); bmesh.ops.translate(tb, vec=(x, y, h), verts=tb.verts)
        me = bpy.data.meshes.new("t"); tb.to_mesh(me); tb.free(); bm.from_mesh(me); bpy.data.meshes.remove(me); n += 1
    me = bpy.data.meshes.new("TREES"); bm.to_mesh(me); bm.free(); ob = bpy.data.objects.new("TREES", me); col().objects.link(ob); ob.data.materials.append(bpy.data.materials["PJ_TREE"])
    return "trees: {}".format(n)

def stage_ground():
    bpy.ops.mesh.primitive_plane_add(size=2000, location=(0, 0, -0.3)); g = bpy.context.active_object; g.name = "GROUND"
    for c in g.users_collection: c.objects.unlink(g)
    col().objects.link(g); g.data.materials.append(bpy.data.materials["PJ_GROUND"]); return "ground"


# ---------- 188 Lafayette itself (the Sing Tao building, 413 Broome) ----------
# Body = the city's outline at its recorded roof (60.07 ft, 5 floors, built 1999). The building is the SW corner of Broome x Lafayette:
# Lafayette runs down its EAST side (outline points 5-6-0), Broome is its NORTH end (points 5-4). Corner = outline point 5.
# Facade detail INFERRED from Parasol's listing photos + Joshua's Street View, 2026-10-08. Feet are measured from the corner.
CORNER = (-73.998395376221, 40.721042374639); LAF_S = (-73.998616527288, 40.720779485378); BROOME_W = (-73.998469820982, 40.721073855671)
ROOF = 60.07 * FT; GF = 13 * FT; NFL = 5                                       # pink ground floor measures ~13 ft in the Broome photo
def _box(bm, x0, x1, y0, y1, z0, z1):
    x0, x1 = min(x0, x1), max(x0, x1); y0, y1 = min(y0, y1), max(y0, y1)
    vs = [bm.verts.new(p) for p in ((x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1))]
    for f in ((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)): bm.faces.new([vs[i] for i in f])
MATS = ("PJ_WOOD", "PJ_PLASTER", "PJ_SHOPGLASS", "PJ_FLOOR", "PJ_WHITE", "PJ_SITE", "PJ_GLASS", "PJ_TRIM", "PJ_IRON", "PJ_TAN", "PJ_PINK", "PJ_SIGN", "PJ_COBRA", "PJ_TIGER", "PJ_RED")
def _face(name, a_ll, b_ll, side, draw):
    """One facade. Local frame: x along the face in FEET from a, d = metres out over the sidewalk, z metres up."""
    a = proj(*a_ll); b = proj(*b_ll); ang = math.atan2(b[1]-a[1], b[0]-a[0]); L = math.dist(a, b) / FT
    parts = {k: bmesh.new() for k in MATS}
    def B(mat, x0, x1, d0, d1, z0, z1): _box(parts[mat], x0 * FT, x1 * FT, side * d0, side * d1, z0, z1)
    def D(mat, cx, cz, size, bar=0.12):
        # brick diamond: a square frame turned 45 degrees in the wall plane (cx feet along, cz metres up)
        bm = parts[mat]; before = set(bm.verts); s = size * FT / 2
        for x0, x1, z0, z1 in ((-s, s, -s, -s + bar), (-s, s, s - bar, s), (-s, -s + bar, -s, s), (s - bar, s, -s, s)): _box(bm, x0, x1, 0, side * 0.06, z0, z1)
        new = [v for v in bm.verts if v not in before]
        bmesh.ops.rotate(bm, verts=new, cent=(0, 0, 0), matrix=__import__('mathutils').Matrix.Rotation(math.radians(45), 3, 'Y'))
        bmesh.ops.translate(bm, verts=new, vec=(cx * FT, 0, cz))
    B.D = D
    cuts = []
    def CUT(x0, x1, d0, d1, z0, z1): cuts.append((x0 * FT, x1 * FT, side * d0, side * d1, z0, z1))   # hole through the massing
    B.cut = CUT
    draw(B, L)
    root = bpy.data.objects.new("B188_" + name, None); col().objects.link(root); root.location = (a[0], a[1], 0.14); root.rotation_euler = (0, 0, ang)
    for mat, bm in parts.items():
        if not bm.faces: bm.free(); continue
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces); me = bpy.data.meshes.new("B188_" + name + mat[2:]); bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new("B188_" + name + mat[2:], me); col().objects.link(ob); ob.parent = root; ob.data.materials.append(bpy.data.materials[mat])
    for i, c in enumerate(cuts):
        cb = bmesh.new(); _box(cb, c[0], c[1], c[2], c[3], c[4] - 0.2, c[5]); me = bpy.data.meshes.new("CUT"); cb.to_mesh(me); cb.free()
        co = bpy.data.objects.new("B188_CUT_%s_%d" % (name, i), me); col().objects.link(co); co.parent = root; co.hide_render = True; co.display_type = 'WIRE'; co.hide_viewport = True
    return L
def _win(B, x0, x1, z0, z1, panes=1, transom=None, d=0.0, glass="PJ_GLASS", tpanes=None):
    """Black-framed glazing: x in feet, z in metres. transom = height (m) of a top row of glass, split into tpanes (default = panes)."""
    B(glass, x0, x1, d + 0.00, d + 0.05, z0, z1)
    f = 0.25                                                                                  # frame width, feet
    zt = z1 - transom if transom else z1
    for xx in [x0 + (x1 - x0) * i / panes for i in range(panes + 1)]: B("PJ_IRON", xx - f / 2, xx + f / 2, d - 0.01, d + 0.08, z0, zt)
    if transom:
        tp = tpanes or panes
        bars = [x0 + (x1 - x0) * fr for fr in [0.0] + list(tp) + [1.0]] if isinstance(tp, (list, tuple)) else [x0 + (x1 - x0) * i / tp for i in range(tp + 1)]
        for xx in bars: B("PJ_IRON", xx - f / 2, xx + f / 2, d - 0.01, d + 0.08, zt, z1)
    for zz in ([z0, z1] + ([zt] if transom else [])): B("PJ_IRON", x0 - f / 2, x1 + f / 2, d - 0.01, d + 0.08, zz - 0.04, zz + 0.04)
def _bay(B, x0, x1, door=None, awning=True):
    """Parasol storefront bay (photo listing/photos/parasol_bays_awnings.webp): heavy black steel surround, frameless glass,
    glass doors with bar pulls, black retractable awning run out over the sidewalk. Everything dark."""
    s = 0.7                                                                                   # surround width, feet
    B("PJ_SHOPGLASS", x0 + s, x1 - s, 0.00, 0.04, 0.12, GF - 1.05)
    for xx in (x0, x1 - s): B("PJ_IRON", xx, xx + s, -0.01, 0.12, 0.0, GF - 0.85)             # jambs
    B("PJ_IRON", x0, x1, -0.01, 0.12, GF - 1.05, GF - 0.85)                                    # head
    B("PJ_IRON", x0, x1, -0.01, 0.12, 0.0, 0.12)                                               # sill
    if door:
        for xx in door: B("PJ_TRIM", xx, xx + 0.1, 0.05, 0.10, 0.9, 2.1)                      # bar pulls
        B("PJ_IRON", door[0] - 3.0, door[0] - 2.9, 0.0, 0.05, 0.12, GF - 1.05)               # thin door edge line in the glass
    if awning:
        B("PJ_IRON", x0 - 0.3, x1 + 0.3, 0.0, 0.30, GF - 0.80, GF - 0.55)                     # roller housing on the wall
        B("PJ_IRON", x0 - 0.2, x1 + 0.2, 0.30, 1.05, GF - 0.92, GF - 0.86)                    # fabric run out ~3.5 ft
        B("PJ_IRON", x0 - 0.2, x1 + 0.2, 1.00, 1.07, GF - 1.10, GF - 0.86)                    # front bar / valance
        for xx in (x0 + 0.5, x1 - 0.7): B("PJ_IRON", xx, xx + 0.2, 0.10, 1.00, GF - 0.95, GF - 0.90)   # arms
def _ribbons(B, L, runs, first=None):
    """Upper floors: horizontal window bands (x0, x1 feet, panes) on every floor; `first` = extra runs on the 2nd floor only."""
    fh = (ROOF - GF) / (NFL - 1)
    for fl in range(NFL - 1):
        z = GF + fl * fh
        for x0, x1, n in runs + (first if (first and fl == 0) else []): _win(B, x0, x1, z + 0.75, z + 2.35, panes=n)
    B("PJ_TRIM", 0, L, -0.02, 0.12, ROOF - 0.12, ROOF + 0.05)                                 # coping
def _lafayette(B, L):
    # x = feet south from the Broome corner. From Michael's photos 2026-10-08 (listing/photos/) + Parasol's plan (listing/parasol_188_floorplan.pdf).
    # Parasol = 68.6 ft and runs to the building's south end, so corner + lobby = 44.7 ft, split by the photo: pink 39.1, lobby 5.6.
    # Re-measured 2026-10-08 from listing/photos/lafayette_pink_scale.webp at ~44 px/ft (people + doors; Broome photo agrees): panes ~3.3 ft,
    # pink run ~30.8 ft, lobby ~5.4 ft. Parasol (68.6 ft per its plan) then runs 36.2-104.8 ft and the building's south end is 104.8-113.3.
    # 2nd pass (Michael): each pane is a shoulder width plus a bit, ~2.2 ft -> window ~11 ft; the photo is stretched sideways, so widths
    # come from that pane size and heights from the people in it. Pink run ~20.2 ft, lobby ~4.5 ft, Parasol 24.7-93.3 ft, building to 113.3.
    P0 = 20.2; C = 24.7
    # Ceremonia: pink base, NO door on Lafayette (Michael), one wide window (4 panes + a row of transom lights), black frame
    _wall(B, "PJ_PINK", 0, P0, [(3.1, 14.1, 0.10, 2.85)], GF)                                  # pink = paint, flush
    _win(B, 3.1, 14.1, 0.10, 2.85, panes=5, transom=0.55, d=-0.08, glass="PJ_SHOPGLASS", tpanes=[0.37, 0.57])   # 3 unequal transoms   # 5 thin panes, 3 transoms
    # Sing Tao entrance for the offices upstairs (not a shop door): tan brick, black-framed glass double door, white sign above
    _wall(B, "PJ_TAN", P0, C, [(P0 + 0.6, C - 0.6, 0.0, 2.3)], GF)
    _win(B, P0 + 0.6, C - 0.6, 0.0, 2.3, panes=2, d=-0.08, glass="PJ_SHOPGLASS")
    B("PJ_SIGN", P0 + 0.2, C - 0.2, 0.06, 0.16, 2.55, 3.75); B("PJ_RED", P0 + 2.6, C - 0.6, 0.16, 0.18, 3.05, 3.55)
    # Parasol (PJ's unit): kitchen front = roll-down shutter with the cobra mural, then three bays, then the 11'-2" wall
    B("PJ_TAN", C, C + 9.6, 0.0, 0.006, 0.0, GF)
    B("PJ_COBRA", C + 0.4, C + 9.2, 0.006, 0.03, 0.0, GF - 0.95)                               # shutter, nearly flush
    for x0, x1, door in ((C + 9.6, C + 23.8, (C + 12.6, C + 13.2)), (C + 25.8, C + 40.1, None), (C + 42.0, C + 56.8, (C + 44.8, C + 45.4))):
        _bay(B, x0, x1, door=door)
    for x0, x1 in ((C + 23.8, C + 25.8), (C + 40.1, C + 42.0)): B("PJ_TAN", x0, x1, 0.0, 0.12, 0.0, GF)   # the two columns
    B("PJ_TAN", C + 56.8, C + 68.6, 0.0, 0.25, 0.0, GF)                                       # 11'-2" solid wall, stands proud
    B("PJ_TAN", C + 68.6, L, 0.0, 0.006, 0.0, GF)                                            # building, south end
    B("PJ_TIGER", C + 57.3, C + 68.1, 0.25, 0.28, 0.2, GF - 0.6)                                # mural on it (Parasol photo)
    # hollow ground floor so the glass looks into rooms: clear height 11'-5" (Parasol plan), 0.25 m walls kept at the back and ends
    CEIL = 11.42 * FT; DEEP = 7.17 - 0.25
    B.cut(2.0, L - 0.8, -DEEP, 0.02, 0.0, CEIL)
    B("PJ_FLOOR", 2.0, L - 0.8, -DEEP, 0.0, -0.02, 0.0)                                       # concrete floor
    B("PJ_WHITE", 2.0, L - 0.8, -DEEP, -DEEP + 0.05, 0.0, CEIL)                               # back wall, white
    B("PJ_WHITE", 2.0, L - 0.8, -DEEP, 0.0, CEIL - 0.03, CEIL)                                # ceiling, white
    for xx in (P0, C - 0.4): B("PJ_WHITE", xx, xx + 0.4, -DEEP, -0.05, 0.0, CEIL)             # walls either side of the lobby
    # Ceremonia is 750 sq ft: over ~30 ft of frontage that is the full depth. The Broome black side door (18.6-21.7 ft west of the
    # corner) gets a small stair/egress enclosure in the back corner by Broome. INFERRED.
    B("PJ_WHITE", 2.5, 9.0, -DEEP + 1.35, -DEEP + 1.45, 0.0, CEIL)                            # kept 2.5 ft off the Broome wall:
    B("PJ_WHITE", 8.9, 9.0, -DEEP, -DEEP + 1.45, 0.0, CEIL)                                   # the corner is ~93.6 deg, not square
    # Ceremonia fit-out, per Michael 2026-10-08: from the Broome front door, a bathroom in the back-left corner (Lafayette wall x the
    # lobby-side wall, behind the solid pink 29.5-39.1 ft) and the cash wrap next to it along the back wall. Sizes are typical, not measured.
    BX0 = P0 - 6.0; BD = 2.0                                                                  # bathroom 6 ft along Lafayette x 6.5 ft deep, behind the solid pink
    B("PJ_PLASTER", BX0, BX0 + 0.35, -BD, -0.02, 0.0, CEIL)                                   # front wall facing the shop: solid, no door
    # side wall toward the cash wrap; the door is here, opening into the staff space, not visible from the front door
    B("PJ_PLASTER", BX0, P0 - 2.9, -BD - 0.1, -BD, 0.0, CEIL)
    B("PJ_PLASTER", P0 - 0.2, P0, -BD - 0.1, -BD, 0.0, CEIL)
    B("PJ_PLASTER", P0 - 2.9, P0 - 0.2, -BD - 0.1, -BD, 2.13, CEIL)                           # over the door
    B("PJ_WOOD", P0 - 2.85, P0 - 0.25, -BD - 0.06, -BD - 0.02, 0.0, 2.10)                      # door, 2.6 ft
    B("PJ_WHITE", BX0 + 0.6, BX0 + 2.0, -1.25, -0.55, 0.0, 0.42); B("PJ_WHITE", BX0 + 0.4, BX0 + 1.2, -1.2, -0.6, 0.42, 0.80)   # WC
    B("PJ_WHITE", BX0 + 3.0, BX0 + 4.6, -0.55, -0.05, 0.80, 0.90)                              # wall-hung sink
    # cash wrap: plaster body, walnut top, 6 ft long, ~3 ft of staff space behind it (the bathroom door opens into it)
    B("PJ_PLASTER", P0 - 5.1, P0 - 3.1, -BD - 2.2, -BD - 0.4, 0.0, 0.94)
    B("PJ_WOOD", P0 - 5.2, P0 - 3.0, -BD - 2.25, -BD - 0.35, 0.94, 0.98)
    # blade signs: Ceremonia at the corner, Sing Tao Daily over the Parasol glass
    B("PJ_IRON", 2.0, 2.5, 0.15, 1.05, GF + 0.6, GF + 3.6)
    B("PJ_SIGN", 58.0, 58.5, 0.15, 1.20, GF + 0.8, GF + 4.6); B("PJ_RED", 57.9, 58.6, 0.30, 1.05, GF + 3.6, GF + 4.4)
    # upper floors: wide bands; 2nd floor has the 5-pane band over Ceremonia, the 2-pane window over the lobby and the brick diamond
    _ribbons(B, L, [(2.5, 13.9, 5), (30.0, 46.0, 4), (52.0, 68.0, 4), (74.0, 90.0, 4), (96.0, 112.0, 4)], first=[(P0 + 0.5, C - 0.3, 2)])
    B.D("PJ_TRIM", 17.2, GF + 1.6, 3.0)
def _wall(B, mat, x_from, x_to, holes, h, d0=0.0, d1=0.006):
    """Paint skin flush on the wall face (d0..d1 m, a few mm proud so it shows) from x_from to x_to (feet), z 0..h, with holes cut out."""
    holes = sorted(holes); x = x_from
    for x0, x1, z0, z1 in holes:
        if x0 > x: B(mat, x, x0, d0, d1, 0.0, h)
        if z0 > 0: B(mat, x0, x1, d0, d1, 0.0, z0)
        if z1 < h: B(mat, x0, x1, d0, d1, z1, h)
        x = x1
    if x < x_to: B(mat, x, x_to, d0, d1, 0.0, h)
def _broome(B, L):
    # x = feet west from the corner, from the Broome photos (listing/photos/broome_face.webp, broome_doors_inset.webp):
    # whole ground floor pink, NO overhangs. BOTH doors sit deep in pink-lined openings; the window is near the face.
    R = 0.75                                                                                  # door recess back from the wall face (m)
    win = (3.6, 10.4, 0.05, 2.87); door = (12.7, 15.8, 0.0, 2.83); side = (18.6, 21.7, 0.0, 3.20)   # window runs to the ground
    _wall(B, "PJ_PINK", 0, L, [win, door, side], GF)                                          # pink = paint, flush
    _win(B, win[0], win[1], win[2], win[3], panes=2, d=-0.10, glass="PJ_SHOPGLASS")
    B.cut(win[0] + 0.1, win[1] - 0.1, -1.2, 0.02, win[2], win[3])                              # open the wall behind it into the shop                             # Ceremonia window, small reveal
    for x0, x1, z0, z1 in (door, side):
        B.cut(x0, x1, -R, 0.02, z0, z1)                                                       # cut the recess into the building
        B("PJ_PINK", x0, x0 + 0.15, -R, 0.0, z0, z1); B("PJ_PINK", x1 - 0.15, x1, -R, 0.0, z0, z1)   # pink reveal sides
        B("PJ_PINK", x0, x1, -R, 0.0, z1 - 0.05, z1)                                          # pink head
        if (x0, x1) == (side[0], side[1]): B("PJ_IRON", x0, x1, -R - 0.05, -R, z0, z1)       # solid back behind the side door only
    # Ceremonia glass door: black frame, glass door to 2.3 m, dark panel above, at the back of the recess
    _win(B, door[0] + 0.15, door[1] - 0.15, 0.0, 2.30, panes=1, d=-R + 0.02, glass="PJ_SHOPGLASS")
    B("PJ_TRIM", door[1] - 0.8, door[1] - 0.7, -R + 0.08, -R + 0.14, 0.9, 1.9)
    # side door: black door to 2.35 m, sign panel to 2.8 m, louvre to the head, all at the back of the recess
    B("PJ_IRON", side[0] + 0.15, side[1] - 0.15, -R + 0.01, -R + 0.05, 0.0, 2.35)
    B("PJ_SIGN", side[0] + 0.15, side[1] - 0.15, -R + 0.01, -R + 0.04, 2.38, 2.78)
    for k in range(6): B("PJ_TRIM", side[0] + 0.15, side[1] - 0.15, -R + 0.01, -R + 0.06, 2.82 + k * 0.06, 2.84 + k * 0.06)   # louvre slats
    B("PJ_IRON", 16.4, 18.0, -0.01, 0.015, 0.37, 0.79)                                         # low vent, flush
    _ribbons(B, L, [(2.8, 15.5, 2), (18.6, 21.6, 1)])
def stage_building():
    for o in [o for o in bpy.data.objects if o.name.startswith("B188_")]: bpy.data.objects.remove(o, do_unlink=True)
    # Lafayette is east of the building: walking corner -> south it is on the left (+y). Broome is north: corner -> west, on the right (-y).
    La = _face("LAFAYETTE", CORNER, LAF_S, +1, _lafayette)
    Lb = _face("BROOME", CORNER, BROOME_W, -1, _broome)
    bpy.context.view_layer.update(); site = bpy.data.objects.get("SITE_188_LAF")
    for co in [o for o in bpy.data.objects if o.name.startswith("B188_CUT_")]:
        m = site.modifiers.new("cut", 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.object = co
        try: m.solver = 'EXACT'
        except Exception: pass
        with bpy.context.temp_override(object=site, active_object=site): bpy.ops.object.modifier_apply(modifier=m.name)
    return "building: Lafayette front {:.1f} ft, Broome front {:.1f} ft, roof {:.1f} ft".format(La, Lb, ROOF / FT)

def stage_cameras():
    sc = bpy.context.scene
    if not bpy.data.objects.get("SUN"):
        bpy.ops.object.light_add(type='SUN', location=(0, 0, 300)); s = bpy.context.active_object; s.name = "SUN"; s.data.energy = 3.0; s.rotation_euler = (math.radians(50), 0, math.radians(35))
    w = sc.world or bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
    bg = next((n for n in w.node_tree.nodes if n.type == "BACKGROUND"), None)
    if bg: bg.inputs[0].default_value = (0.08, 0.075, 0.07, 1); bg.inputs[1].default_value = 1.0
    for name, loc, rot, ortho in (("CAM_PLAN", (0, 0, 600), (0, 0, math.radians(29)), 560), ("CAM_WIDE", (0, 0, 600), (0, 0, math.radians(29)), 900)):
        cam = bpy.data.objects.get(name)
        if not cam:
            cd = bpy.data.cameras.new(name); cam = bpy.data.objects.new(name, cd); sc.collection.objects.link(cam)
        cam.location = loc; cam.rotation_euler = rot; cam.data.type = 'ORTHO'; cam.data.ortho_scale = ortho; cam.data.clip_end = 2000
    axon = bpy.data.objects.get("CAM_AXON")
    if not axon:
        cd = bpy.data.cameras.new("CAM_AXON"); axon = bpy.data.objects.new("CAM_AXON", cd); sc.collection.objects.link(axon)
    axon.location = (-260, -420, 420); axon.rotation_euler = (math.radians(50), 0, math.radians(-29)); axon.data.type = 'ORTHO'; axon.data.ortho_scale = 700; axon.data.clip_end = 3000
    engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
    for eng in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'BLENDER_WORKBENCH'):
        if eng in engines:
            try: sc.render.engine = eng; break
            except TypeError: continue
    sc.render.resolution_x = 1800; sc.render.resolution_y = 1200; sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 90
    return "cameras: plan, wide, axon; engine " + sc.render.engine

def render(cam_name, filename):
    sc = bpy.context.scene; sc.camera = bpy.data.objects[cam_name]; os.makedirs(os.path.join(OUT_DIR, "frames"), exist_ok=True)
    sc.render.filepath = os.path.join(OUT_DIR, "frames", filename)
    bpy.ops.render.render(write_still=True); return "rendered " + sc.render.filepath

def export_glb(filename="lafayette_188.glb"):
    for o in bpy.data.objects: o.select_set(False)
    names = ["SOHO_MASSING", "SITE_188_LAF", "ROADBED", "SIDEWALK", "MEDIAN", "GROUND", "TREES"] + [o.name for o in bpy.data.objects if o.name.startswith("ST_") or (o.name.startswith("B188_") and not o.hide_viewport)]
    for n in names:
        o = bpy.data.objects.get(n)
        if o: o.select_set(True)
    bpy.context.view_layer.objects.active = bpy.data.objects["SOHO_MASSING"]
    path = os.path.join(OUT_DIR, "assets", filename); os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6, export_apply=True, export_cameras=False, export_lights=False, export_yup=True)
    return "exported {} {:.0f} KB".format(path, os.path.getsize(path) / 1024)

def site_center():
    """glTF-space position of the site (x east, y up, z south) for the page's camera waypoints."""
    ob = bpy.data.objects.get("SITE_188_LAF")
    if not ob or not ob.data.vertices: return None
    xs = [v.co.x for v in ob.data.vertices]; ys = [v.co.y for v in ob.data.vertices]
    return [round(sum(xs)/len(xs), 1), 0, round(-sum(ys)/len(ys), 1)]


if __name__ == "__main__" or bpy.app.background:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    log = []
    for fn in (stage_massing, stage_flat, stage_labels, stage_trees, stage_ground, stage_building, stage_cameras):
        log.append(fn()); print(log[-1], flush=True)
    pts = {"site": site_center(), "spring_6": [round(v, 1) for v in proj(-73.997141, 40.722301)], "canal_st": [round(v, 1) for v in proj(-74.000193, 40.718803)],
           "prince_rw": [round(v, 1) for v in proj(-73.997702, 40.724329)], "bway_laf": [round(v, 1) for v in proj(-73.996204, 40.725297)]}
    json.dump(pts, open(os.path.join(OUT_DIR, "data", "model_points.json"), "w")); print("points", pts, flush=True)
    for cam, fn in (("CAM_PLAN", "map_plan.jpg"), ("CAM_AXON", "map_axon.jpg"), ("CAM_WIDE", "map_wide.jpg")):
        try: print(render(cam, fn), flush=True)
        except Exception as e: print("render failed", cam, e, flush=True)
    try: print(export_glb(), flush=True)
    except Exception as e: print("export failed", e, flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR, "build", "lafayette_188.blend"))
    print("BUILD DONE", flush=True)
