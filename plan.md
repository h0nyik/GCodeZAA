# Plán: Nahrazení open3d → trimesh

## Kontext

Cíl: Nahradit `open3d` (chybí Linux ARM64 wheels) za `trimesh` (pure Python,
wheels pro všechny platformy včetně Raspberry Pi). Výsledek: plně funkční
ZAA processing na macOS, Windows, Linux x86, Linux ARM64 (RPi 4/5).

---

## Analýza současného stavu

### Kde a jak se open3d používá

| Soubor | open3d API | Popis |
|--------|-----------|-------|
| `process.py:52` | `open3d.t.io.read_triangle_mesh(path, enable_post_processing=True)` | Načtení STL/OBJ souboru |
| `process.py:53` | `mesh.get_min_bound()` | Min XYZ bounding box (pro přesunutí na podložku) |
| `process.py:54` | `mesh.get_max_bound()` | Max XYZ bounding box |
| `process.py:56` | `mesh.translate([dx, dy, dz])` | Přesunutí meshe na správnou pozici |
| `process.py:58` | `open3d.t.geometry.RaycastingScene()` | Vytvoření raycasting scény |
| `process.py:59` | `scene.add_triangles(mesh)` | Přidání meshe do scény |
| `extrusion.py:113` | `scene.cast_rays(open3d.core.Tensor(rays_up, ...))` | Raycast nahoru (N paprsků) |
| `extrusion.py:127` | `scene.cast_rays(open3d.core.Tensor(rays_down, ...))` | Raycast dolů (N paprsků) |
| `extrusion.py:136` | `hits["t_hit"][i].item()` | Vzdálenost k zásahu pro i-tý paprsek |
| `extrusion.py:138` | `hits["primitive_normals"][i]` | Normála plochy v místě zásahu |
| `extrusion.py:141` | `normal[2].item()` | Z složka normály |
| `context.py:20` | `open3d.t.geometry.RaycastingScene` | Typová anotace |

### Klíčový rozdíl v API

**open3d** vrací výsledky pro VŠECHNY paprsky (vč. miss = `t_hit: inf`):
```python
hits = scene.cast_rays(tensor_Nx6)       # vždy N výsledků
t    = hits["t_hit"][i].item()           # float, inf = žádný zásah
n    = hits["primitive_normals"][i]      # (3,) vector
```

**trimesh** vrací jen paprsky, které ZASÁHLY cíl:
```python
locs, ray_idx, tri_idx = mesh.ray.intersects_location(
    ray_origins, ray_directions, multiple_hits=False
)
# locs    = (M, 3) — souřadnice zásahů, M <= N
# ray_idx = (M,)  — index paprsku pro každý zásah
# tri_idx = (M,)  — index trojúhelníku pro každý zásah
```
→ Je potřeba sestavit N-prvkové pole t_hit a normals ručně (miss = inf / zero).

---

## Mapování API

### 1. Načtení meshe

```python
# PŘED (open3d)
mesh = open3d.t.io.read_triangle_mesh(path, enable_post_processing=True)
min_bound = mesh.get_min_bound()   # Tensor
max_bound = mesh.get_max_bound()   # Tensor
center = min_bound + (max_bound - min_bound) / 2
mesh.translate([x - center[0].item(), y - center[1].item(), -min_bound[2].item()])

# PO (trimesh)
import trimesh
import numpy as np
mesh = trimesh.load(path, force="mesh")
min_bound = mesh.bounds[0]   # np.ndarray (3,)
max_bound = mesh.bounds[1]   # np.ndarray (3,)
center = (min_bound + max_bound) / 2
mesh.apply_translation([x - center[0], y - center[1], -min_bound[2]])
```

### 2. Vytvoření scény

```python
# PŘED (open3d)
scene = open3d.t.geometry.RaycastingScene()
scene.add_triangles(mesh)
return scene

# PO (trimesh) — mesh JE scéna, žádný extra wrapper nepotřeba
return mesh   # trimesh.Trimesh objekt
```

### 3. Raycast (jádro změny — extrusion.py)

```python
# PŘED (open3d)
hits_up = scene.cast_rays(
    open3d.core.Tensor(rays_up, dtype=open3d.core.Dtype.Float32)
)
hit_up   = max(0, abs(hits_up["t_hit"][i].item()))
normal_up = hits_up["primitive_normals"][i]

# PO (trimesh)
def cast_rays_trimesh(mesh, rays):
    """
    rays: list of [ox, oy, oz, dx, dy, dz]
    Vrací: t_hit (N,), normals (N, 3)
    Miss = t_hit[i] = inf, normals[i] = [0, 0, 0]
    """
    origins    = np.array([[r[0], r[1], r[2]] for r in rays], dtype=np.float32)
    directions = np.array([[r[3], r[4], r[5]] for r in rays], dtype=np.float32)
    n = len(rays)

    t_hit   = np.full(n, np.inf,     dtype=np.float32)
    normals = np.zeros((n, 3),       dtype=np.float32)

    locs, ray_idx, tri_idx = mesh.ray.intersects_location(
        ray_origins=origins,
        ray_directions=directions,
        multiple_hits=False,
    )
    if len(ray_idx):
        dists = np.linalg.norm(locs - origins[ray_idx], axis=1)
        t_hit[ray_idx]      = dists
        normals[ray_idx]    = mesh.face_normals[tri_idx]

    return t_hit, normals
```

Použití v `contour_z()`:
```python
# PŘED
hits_up = scene.cast_rays(open3d.core.Tensor(rays_up, ...))
hit_up  = max(0, abs(hits_up["t_hit"][i].item()))
nz_up   = hits_up["primitive_normals"][i][2].item()

# PO
t_up, n_up = cast_rays_trimesh(mesh, rays_up)
hit_up = max(0, abs(float(t_up[i])))
nz_up  = float(n_up[i][2])
```

### 4. Typové anotace (context.py)

```python
# PŘED
import open3d
exclude_object: dict[str, open3d.t.geometry.RaycastingScene] = {}
active_object:  open3d.t.geometry.RaycastingScene | None = None

# PO
import trimesh
exclude_object: dict[str, trimesh.Trimesh] = {}
active_object:  trimesh.Trimesh | None = None
```

---

## Soubory ke změně

### `gcodezaa/process.py`
- [ ] `import open3d` → `import trimesh`, `import numpy as np`
- [ ] Funkce `load_object()`: celé tělo (~10 řádků)
- [ ] Návratový typ: `open3d.t.geometry.RaycastingScene` → `trimesh.Trimesh`

### `gcodezaa/extrusion.py`
- [ ] `import open3d` → `import numpy as np`
- [ ] Přidat helper funkci `cast_rays_trimesh(mesh, rays)` (~15 řádků)
- [ ] Typ parametru `scene` → `mesh: trimesh.Trimesh` v `contour_z()`
- [ ] 2× `scene.cast_rays(open3d.core.Tensor(...))` → `cast_rays_trimesh(mesh, ...)`
- [ ] Přístup k `hits["t_hit"][i].item()` → `float(t_hit[i])`
- [ ] Přístup k `hits["primitive_normals"][i][2].item()` → `float(normals[i][2])`

### `gcodezaa/context.py`
- [ ] `import open3d` → `import trimesh`
- [ ] 2× typová anotace

### `pyproject.toml`
- [ ] Odebrat `open3d` z dependencies
- [ ] Přidat `trimesh >= 4.0`
- [ ] Přidat `numpy >= 1.24` (explicitně, trimesh na něm závisí)

### `requirements-gui.txt`
- [ ] Přidat `trimesh>=4.0`

### `build_ci.py`
- [ ] Odebrat `--collect-all open3d`
- [ ] Přidat `--collect-all trimesh`
- [ ] Odebrat `NO_OPEN3D` logiku

### `.github/workflows/build.yml`
- [ ] Odebrat `no_open3d` z matrix
- [ ] Odebrat podmíněné kroky pro open3d/stub
- [ ] Unifikovat: všechny platformy stejný postup
- [ ] Přidat `pip install trimesh numpy` do Python deps

### `GCodeZAA.spec` (lokální macOS build)
- [ ] Odebrat open3d binaries (`libtbb`, `libomp`, `pybind.so`)
- [ ] Odebrat `open3d` z datas
- [ ] Přidat `trimesh` do datas
- [ ] Výsledná .app bude výrazně menší (trimesh ~5 MB vs open3d ~300 MB)

---

## Výkonnostní srovnání

| | open3d | trimesh (pure Python) | trimesh + pyembree |
|---|---|---|---|
| Backend | C++ BVH + Intel TBB | NumPy + Python | Intel Embree C++ |
| ARM64 Linux | ❌ | ✅ | ❌ (Embree = x86 only) |
| Rychlost (1000 paprsků) | ~1 ms | ~50–200 ms | ~2 ms |
| Dopad na GCodeZAA | — | +1–5 s/model | zanedbatelný |

Pro typický print (100–500 paprsků/vrstva × 60 vrstev = ~30 000 paprsků):
- open3d: < 0.5 s
- trimesh pure Python: 5–20 s
- trimesh + pyembree (x86): < 1 s

**Závěr**: Pro interaktivní GUI (post-processing po tisku, ne real-time) je
5–20 s zcela přijatelných. Na x86 lze volitelně nainstalovat `pyembree`
pro rychlost srovnatelnou s open3d.

---

## Testovací plán

Po implementaci ověřit:

1. **Funkční test** — spustit na `test/3` gcode, porovnat počet konturovaných
   segmentů (očekáváno: 184) a rozsah Z korekcí (max +0.120 mm)
2. **Numerická shoda** — delta Z na identických raycastech musí být < 0.001 mm
   oproti open3d výstupu (floating point rozdíly jsou přijatelné)
3. **Chybové stavy** — neexistující STL, prázdný mesh, zero-triangle mesh
4. **Platformy** — ověřit import a základní raycast na macOS arm64, Linux x86,
   Linux arm64 (RPi nebo ARM runner v CI)
5. **Build** — `build_ci.py` projde na všech 5 platformách bez `NO_OPEN3D`

---

## Výhody po implementaci

| Vlastnost | open3d | trimesh |
|---|---|---|
| Linux ARM64 (RPi 4/5) | ❌ | ✅ |
| Velikost .app / .exe | ~600 MB | ~50 MB |
| Čas instalace pip | ~2 min | ~10 s |
| Čas CI buildu | ~8 min | ~3 min |
| Python 3.13+ | ❌ (max 3.12) | ✅ |
| Závislosti | ASSIMP, TBB, libomp, ... | numpy, scipy (optional) |
| Licence | MIT | MIT |

---

## Co se NEMĚNÍ

- Algoritmus ZAA (segmentace, E korekce, RESET_Z) — beze změny
- GUI (`gui.py`) — beze změny
- G-code parsing (`process.py` logika) — beze změny
- Výstupní formát G-code — identický
