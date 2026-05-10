# Ashley VRM Rig — Coordinate System Reference

> **v2 — Calibrado con 17 PNGs hi-res (1 por bone), framing close-up.**
> Todos los axis verificados visualmente al 95-100%.
>
> Para poses naturales, usar **fracción** de los 45° del test (10-30%) para que sea sutil.

---

## Convenciones generales

### Mirror izquierdo/derecho (CONFIRMADO)
Los bones de left/right son **mirrors exactos**, los axes Z están invertidos:
- right Z+ = down → left Z- = down
- right Z+ = open → left Z- = open
- X y Y son iguales en ambos lados (con algunas excepciones por la convención del bone)

### Axis longitudinal (twist invisible)
- Para `upperArm`, `lowerArm`, `upperLeg`, `lowerLeg`: el **eje Y** es la longitud del hueso. Rotar Y solo hace **twist** (gira hueso sobre sí mismo, casi invisible salvo si el hijo cambia orientación).

---

## Bones del torso central

### `head` ✅ — el más usado (idle, look at user, mood reactions)

| Axis | Efecto observado | Uso |
|------|------------------|------|
| **X+ 45°** | Chin **UP** (mira ARRIBA, throat exposed, hyperextend back) | proud / surprised |
| **X- 45°** | Chin **DOWN** (mira ABAJO, chin to chest, hair forward) | shy / nodding "sí" |
| **Y+ 45°** | Head gira a SU IZQUIERDA (vemos perfil DERECHO de Ashley) | tsundere look-away |
| **Y- 45°** | Head gira a SU DERECHA (vemos perfil IZQUIERDO de Ashley) | look right |
| **Z+ 45°** | Head **tilt** a SU DERECHA (oreja derecha al hombro derecho) | curious tilt right |
| **Z- 45°** | Head **tilt** a SU IZQUIERDA (oreja izquierda al hombro izquierdo) | curious tilt left |

> ⚠️ **Bug conocido:** rotar head deja la mesh interior (boca roja) flotando. Pendiente fix Emiko.

### `neck` — mismo comportamiento que head pero a nivel cervical

| Axis | Efecto |
|------|--------|
| X+ | chin UP (head extension) |
| X- | chin DOWN (head flexion) |
| Y+ | gira a su izquierda |
| Y- | gira a su derecha |
| Z+ | tilt a su derecha |
| Z- | tilt a su izquierda |

> Para movimientos de cabeza en idle, **usar `head` no `neck`** (el head solo afecta la cabeza, el neck mueve también la base — más rígido).

### `chest` — torso superior (zona pectoral)

| Axis | Efecto |
|------|--------|
| **X+ 45°** | Pecho **back arch** (chest out, espalda arqueada hacia atrás) |
| **X- 45°** | Pecho **forward** (slouch, chin to chest, encorvar) |
| **Y+ 45°** | Torso twist a SU IZQUIERDA (hombro izquierdo va atrás) |
| **Y- 45°** | Torso twist a SU DERECHA |
| **Z+ 45°** | Torso lean a SU IZQUIERDA (hombro izquierdo baja) |
| **Z- 45°** | Torso lean a SU DERECHA |

> **Idle breathing:** `chest.rotation.x = sin(t * 1.4) * 0.025` para subida/bajada sutil

### `spine` — torso bajo (zona lumbar)

Igual que `chest` pero pivote más bajo:
- X+ = back arch lumbar
- X- = bend forward (encorvar lumbar)
- Y+/- = twist desde caderas
- Z+/- = side bend

### `hips` — RAÍZ (rota TODO el cuerpo)

| Axis | Efecto |
|------|--------|
| **X+ 45°** | Cuerpo entero se inclina hacia ATRÁS (back arch grande) |
| **X- 45°** | Cuerpo entero se inclina hacia DELANTE (bowing, "plancha") |
| **Y+ 45°** | Cuerpo gira a SU IZQUIERDA (perfil derecho hacia cámara) |
| **Y- 45°** | Cuerpo gira a SU DERECHA (perfil izquierdo hacia cámara) |
| **Z+ 45°** | Cuerpo cae lateralmente a SU IZQUIERDA (lying horizontal) |
| **Z- 45°** | Cuerpo cae lateralmente a SU DERECHA |

> Usar valores PEQUEÑOS (≤5°) para hipshot natural.

---

## Brazo derecho (right side)

### `rightUpperArm` (hombro a codo) — desde T-pose (sin rest)

| Axis | Efecto |
|------|--------|
| **X+ 45°** | Brazo va hacia ATRÁS del cuerpo (extender atrás) |
| **X- 45°** | Brazo va hacia DELANTE del cuerpo (raise forward) |
| Y+/- | Twist (rota hueso longitudinal — afecta orientación de la mano) |
| **Z+ 45°** | Brazo BAJA desde T-pose (toward body side) ✅ |
| **Z- 45°** | Brazo SUBE desde T-pose (toward overhead) |

> **Rest pose:** `z: PI*0.40, y: -PI*0.04` (~72° abajo, 7° abrir hacia afuera)

### `rightLowerArm` (codo a muñeca)

| Axis | Efecto |
|------|--------|
| X+/- | Twist sutil del antebrazo |
| **Y+ 45°** | Codo flexiona FORWARD (antebrazo hacia el pecho) ✅ |
| Y- | Hyperextension (físicamente imposible) |
| Z+/- | Twist secundario |

> **Rest pose:** `y: PI*0.10` (~18°, carrying angle natural)

### `rightHand` (muñeca + dedos)

> ⚠️ Framing del test demasiado cercano al cuerpo, lectura limitada. Usar valores bajos para evitar romper la pose.

| Axis | Efecto inferido |
|------|------------------|
| X+/- | Mano flex/extension (wrist up/down) |
| Y+/- | Twist mano (pronation/supination) |
| Z+/- | Radial / ulnar deviation |

---

## Brazo izquierdo (left side) — MIRROR de right

### `leftUpperArm`

| Axis | Efecto |
|------|--------|
| **X+ 45°** | Brazo va hacia DELANTE (mirror de right X+) ⚠️ ojo cambia orientación |
| **X- 45°** | Brazo va hacia ATRÁS |
| Y+/- | Twist |
| **Z+ 45°** | Brazo SUBE (overhead) — **MIRROR de right Z-** |
| **Z- 45°** | Brazo BAJA (toward body side) — **MIRROR de right Z+** ✅ |

> **Rest pose:** `z: -PI*0.40, y: PI*0.04`

### `leftLowerArm`

| Axis | Efecto |
|------|--------|
| **Y- 45°** | Codo flexiona FORWARD ✅ — MIRROR de right Y+ |
| Y+ | Hyperextension imposible |

> **Rest pose:** `y: -PI*0.10`

### `leftHand`

Mirror del rightHand, con axes Z flipados.

---

## Piernas

### `rightUpperLeg` / `leftUpperLeg` (cadera a rodilla)

| Axis | Efecto right | Efecto left |
|------|--------------|-------------|
| **X+ 45°** | Pierna va ATRÁS (kick backward) | Pierna va ATRÁS |
| **X- 45°** | Pierna va DELANTE (kick forward) | Pierna va DELANTE |
| Y+/- | Twist | Twist |
| **Z+** | Right: pierna ABRE outward | Left: pierna CIERRA inward |
| **Z-** | Right: pierna CIERRA inward | Left: pierna ABRE outward |

> **Rest pose:** ambas a 0,0,0 (piernas rectas hacia abajo)

### `rightLowerLeg` / `leftLowerLeg` (rodilla a tobillo)

| Axis | Efecto |
|------|--------|
| **X+ 45°** | Rodilla flexiona ATRÁS (talón al glúteo) ✅ — único movimiento útil |
| X- | Hyperextension imposible |
| Y+/- | Twist sutil tibia |
| Z+/- | Casi sin efecto |

### `rightFoot` / `leftFoot` (tobillo + pie)

| Axis | Efecto |
|------|--------|
| **X+ 45°** | Pie point DOWN (plantarflexion, "ballerine punta de pie") |
| **X- 45°** | Pie point UP (dorsiflexion, toes up) |
| Y+/- | Eversion / inversion |
| Z+/- | Mínimo movimiento ankle |

---

## 🐛 Bugs del rig (revisión a Emiko)

### Bug #1 — Interior boca NO sigue al `head` (skinning roto)
Severidad alta. Se ve claramente en HEAD X+ 45° (chin up): la mesh roja interior queda flotando.

### Bug #2 — Falta chest spring bones
Contrato: "spring bones for hair AND chest". Solo entregó hair.

### Bug #3 — Metadata mal seteada
- Author: "undefined" → "Mathieu Beleen"
- Commercial use: "personalNonProfit" → "personalProfit"

### Bug #4 — Preset `sad` vacío, usar `sorrow` (custom) en su lugar
El expressionManager tiene `sad` (preset estándar VRM) pero **no produce cambio visible**.
Emiko añadió `sorrow` como custom — probablemente esa es la implementación real de la cara triste.
- ⚠️ Posiblemente lo mismo con `Joy` custom vs `happy` preset (a confirmar)
- **Workaround para poses:** usar `sorrow` para tristeza, evitar `sad`
- **Mood mapping:** `sad/embarrassed → expression 'sorrow'`, no `'sad'`

---

## REST POSE final calibrada

```js
const REST_POSE = {
  rightUpperArm: { z:  PI * 0.40, y: -PI * 0.04 },  // ~72° abajo, 7° abrir
  leftUpperArm:  { z: -PI * 0.40, y:  PI * 0.04 },  // mirror
  rightLowerArm: { y:  PI * 0.10 },                  // 18° forward bend
  leftLowerArm:  { y: -PI * 0.10 },                  // mirror
};
```

---

## Library de POSES corregida (con axis verificados)

```js
const POSES = {
  // ─── Manos en cadera (proud / confident / tsundere "hmph") ──
  // Brazo arriba con codo doblado → mano hacia la cadera
  hipsHands: {
    // Upper arm: NO bajar tanto (Z menor que rest), Y abrir hacia afuera, X retraso
    rightUpperArm: { z: PI * 0.30, y: -PI * 0.15, x: PI * 0.20 },
    leftUpperArm:  { z: -PI * 0.30, y:  PI * 0.15, x: PI * 0.20 },
    // Lower arm: bend forward grande para que la mano llegue a la cadera
    rightLowerArm: { y: PI * 0.50 },
    leftLowerArm:  { y: -PI * 0.50 },
  },

  // ─── Brazos cruzados (embarrassed / tsundere defensive) ─────
  armsCrossed: {
    // Upper arm: subir un poco (Z menor) + traer hacia delante (X-)
    rightUpperArm: { z: PI * 0.35, x: -PI * 0.12, y: -PI * 0.20 },
    leftUpperArm:  { z: -PI * 0.35, x: -PI * 0.12, y:  PI * 0.20 },
    // Lower arm: gran flexion para que cruce el cuerpo
    rightLowerArm: { y: PI * 0.70 },
    leftLowerArm:  { y: -PI * 0.70 },
  },

  // ─── Saludo (excited / hi) ──────────────────────────────────
  // Solo el brazo derecho se levanta
  wave: {
    // Brazo derecho: Z- para que SUBA (recordar: right Z+ = baja)
    rightUpperArm: { z: -PI * 0.20, x: -PI * 0.15, y: -PI * 0.20 },
    rightLowerArm: { y: PI * 0.45 },
    leftUpperArm:  { z: -PI * 0.40, y: PI * 0.04 },  // izq en rest
    leftLowerArm:  { y: -PI * 0.10 },
  },

  // ─── Pensativa (mano der al mentón) ─────────────────────────
  thinking: {
    // Brazo derecho: subido + hacia delante para que mano llegue a la cara
    rightUpperArm: { z: PI * 0.10, y: -PI * 0.25, x: -PI * 0.15 },
    rightLowerArm: { y: PI * 0.90 },  // flexión casi total
    leftUpperArm:  { z: -PI * 0.40, y: PI * 0.04 },
    leftLowerArm:  { y: -PI * 0.10 },
    head: { z: PI * 0.06, x: -PI * 0.04 },  // tilt + chin up sutil
  },

  // ─── Manos juntas frente al pecho (soft / sweet) ────────────
  handsClasped: {
    rightUpperArm: { z: PI * 0.35, y: -PI * 0.10 },
    leftUpperArm:  { z: -PI * 0.35, y:  PI * 0.10 },
    rightLowerArm: { y: PI * 0.55 },
    leftLowerArm:  { y: -PI * 0.55 },
  },

  // ─── Sorpresa (manos cerca de la cara) ──────────────────────
  surprised: {
    rightUpperArm: { z: PI * 0.20, y: -PI * 0.30, x: -PI * 0.15 },
    leftUpperArm:  { z: -PI * 0.20, y:  PI * 0.30, x: -PI * 0.15 },
    rightLowerArm: { y: PI * 0.85 },
    leftLowerArm:  { y: -PI * 0.85 },
  },

  // ─── Tsundere look-away ─────────────────────────────────────
  // Head Y+ = gira a SU izquierda (vemos su perfil derecho)
  lookAway: {
    head: { y: PI * 0.20, x: PI * 0.04 },  // gira izq + chin up sutil
    rightUpperArm: { z: PI * 0.40, y: -PI * 0.04 },
    leftUpperArm:  { z: -PI * 0.40, y:  PI * 0.04 },
    rightLowerArm: { y: PI * 0.10 },
    leftLowerArm:  { y: -PI * 0.10 },
  },

  // ─── Shy / embarrassed ──────────────────────────────────────
  // Head X- = chin DOWN (mira abajo)
  shy: {
    head: { x: -PI * 0.12, z: -PI * 0.04 },  // chin down + tilt sutil
    rightUpperArm: { z: PI * 0.42, y: PI * 0.05 },  // brazos un poco más juntos
    leftUpperArm:  { z: -PI * 0.42, y: -PI * 0.05 },
    rightLowerArm: { y: PI * 0.30 },
    leftLowerArm:  { y: -PI * 0.30 },
  },

  // ─── Curious head tilt ──────────────────────────────────────
  curious: {
    head: { z: PI * 0.12, y: -PI * 0.06 },  // tilt + ligero giro
    rightUpperArm: { z: PI * 0.40, y: -PI * 0.04 },
    leftUpperArm:  { z: -PI * 0.40, y:  PI * 0.04 },
    rightLowerArm: { y: PI * 0.10 },
    leftLowerArm:  { y: -PI * 0.10 },
  },
};
```

---

## Mapping mood → pose

```js
const MOOD_TO_POSE = {
  excited:     'wave',          // alt: 'hipsHands'
  proud:       'hipsHands',
  tsundere:    'lookAway',      // alt: 'armsCrossed'
  embarrassed: 'shy',
  soft:        'handsClasped',
  surprised:   'surprised',
  default:     null,            // rest pose normal
};
```

---

## Pendientes

1. ✅ **wave** — pose construida por user 9-may, validada visualmente
2. ⏳ Construir resto de poses en el editor: hipsHands, armsCrossed, thinking, handsClasped, surprised, lookAway, shy, curious
3. **Mensaje a Emiko** con los 4 fixes (boca + chest + metadata + sad blendshape vacía)
4. **Integración en Reflex** — `assets/ashley_3d.js` + sustituir portrait_panel

## 🧠 Aprendizajes de poses construidas (live updates)

> Cada vez que el user construye una pose en el editor, anoto aquí lo que aprendo
> sobre cómo combinar bones para obtener efectos predecibles.

### Lección global #1 — Los axes locales rotan con el padre

Mis tests aislados (45° por axis desde T-pose) NO son válidos directamente para
combinaciones. El X/Y/Z de un bone cambia de orientación física según la rotación
de su padre (heredada vía Euler order XYZ).

**Implicación:** para inferir starting points para nuevas poses, partir de la
**rest pose** (brazos abajo) y ajustar incrementalmente, NO desde T-pose.

### Lección global #2 — Mismo axis = efecto distinto según contexto

Ejemplo claro: `lowerArm.rotation.y` en este modelo:
- **Desde T-pose** (brazo horizontal): Y es perpendicular al hueso → Y+ flexiona el codo forward
- **Desde rest pose** (brazo vertical): Y está alineado con el hueso → Y+ es **twist invisible**

**Implicación:** valores enormes en lowerArm.y (ej: `-PI*0.889`) son normales si
el upperArm ya está en rest — solo orientan la muñeca, no bendían el codo.

### Lección global #3 — Las manos pesan en la expresividad

Sin rotaciones explícitas en `hand`, las poses se ven "rígidas". Para gestos
naturales (palma forward, dedos hacia arriba, etc.) se necesitan rotaciones X+Y+Z
en hand. El user usa rangos de hasta `PI*0.4` (~72°) en hand sin que se vea raro.

---

## ✅ Poses validadas

### `wave` (saludo / excited) — construida 9-may
```js
wave: {
  rightUpperArm: { x: PI * 0.167, y: -PI * 0.044, z: PI * 0.400 },
  rightLowerArm: { x: PI * 0.100, y: PI * 0.294 },
  rightHand:     { x: -PI * 0.222, y: -PI * 0.078, z: PI * 0.044 },
  leftUpperArm:  { x: -PI * 0.128, y: PI * 0.040, z: -PI * 0.400 },
  leftLowerArm:  { x: -PI * 0.022, y: -PI * 0.889, z: -PI * 0.056 },
  leftHand:      { x: -PI * 0.244, y: PI * 0.072, z: PI * 0.394 },
  head:          { y: -PI * 0.006, z: -PI * 0.056 },
}
```

### `tsundere` (mano cadera + hipshot) — construida 9-may

35+ bones con dedos curvados detallados, hipshot stance, pose más rica hasta ahora.
Ver código completo en `test_viewer.html` → `POSES.tsundere`.

### `peaceSign` (V sign / playful) — construida 9-may

Brazo derecho levantado con dedos haciendo V (index + middle straight, ring + little curl).
Brazo izquierdo curvado abajo. Ver código completo en `test_viewer.html` → `POSES.peaceSign`.

**Patrones extraídos:**
- Brazo levantado desde rest: `upperArm.x = +0.15-0.20` (con z manteniéndose en rest)
- Codo bent ~50°: `lowerArm.y = +PI*0.30`
- Hand rotation para palma forward: combinación de `x ≈ -PI*0.22, z ≈ PI*0.04`
- Brazo opuesto en rest natural: `upperArm.z = -PI*0.40, x ≈ -PI*0.13` (tiny X+ ajusta levemente)
- leftLowerArm con Y enorme = twist invisible (no rompe la pose)
- Cabeza casi neutral con leve tilt Z para "vida" (`z = -PI*0.056`)

---

### `tsundere` (mano en cadera + hipshot + dedos detallados) — construida 9-may

35+ bones tocados (¡!) — la pose más detallada hasta ahora.

**Patrones extraídos:**
- **rightShoulder** se usa con valores muy pequeños (~PI*0.02-0.13) para ajustar el "clavicle pivot" — sin esto el brazo en cadera queda con el hombro desencajado
- **rightLowerArm.y = PI*0.40** + `rightLowerArm.x = PI*0.19` → bend pronunciado del codo Y angulo lateral, manda el antebrazo hacia la cadera
- **rightHand.y = PI*0.41** → muñeca rotada significativamente para que la palma agarre la cadera
- **rightHand.z = -PI*0.20** → ulnar deviation (la mano se inclina hacia el meñique para acomodar a la cadera)
- **Dedos curvados naturalmente:** Z negativo en distal (~-PI*0.35 a -PI*0.43) cierra el dedo. Combinado con proximal Z positivo da curl realista
- **Pulgar especial:** `Metacarpal` + `Proximal` + `Distal` con axes diferentes (X, Y, Z varios) — el pulgar tiene su propio sistema porque opone al resto de los dedos
- **Hipshot stance** = `rightUpperLeg.y = -PI*0.17` + `leftUpperLeg.y = +PI*0.07` → un lado se rota hacia adentro, el otro hacia afuera, creando el "weight shift" sobre una pierna
- **Pies acompañan el hipshot:** `rightFoot.y = +PI*0.13`, `leftFoot.y = -PI*0.14` → giran ligeramente para no parecer pegados al suelo

### Lección global #4 — Las leg rotations crean "weight shifting" natural

Para hacer que Ashley no parezca un palo plantado, los `upperLeg.y` con signos opuestos
(uno positivo, otro negativo, ambos pequeños) crean un hipshot stance natural.
Combinado con `foot.y` que acompaña el giro, queda muy realista.

### Lección global #5 — Los dedos importan MÁS de lo esperado

En la wave los dedos no se tocaron y se veía OK. En tsundere donde la mano agarra
la cadera, sin curl en los dedos la mano queda como una "tabla" pegada al cuerpo.
Para cualquier pose donde la mano interactúa con el cuerpo (cadera, mentón, etc),
hay que curvar dedos.

**Recipe genérico para "dedos curvados (puño suave)":**
```js
indexProximal:    { z: -PI*0.10, x: -PI*0.30 },  // curl proximal
indexIntermediate:{ z: -PI*0.30 },                 // curl intermedio
indexDistal:      { z: -PI*0.30 },                 // curl distal
// repetir para middle, ring, little con valores similares
// thumb es excepción: usa metacarpal + valores diferentes
```

### Lección global #6 — Shoulder bone (rightShoulder/leftShoulder)

No los habíamos tocado en wave (no hacían falta para "saludar arriba").
En tsundere son críticos: ajustan el pivot del hombro para que el brazo entero
quede orientado correctamente. Valores típicos: `Z = ±PI*0.10-0.15`.

---

### `peaceSign` (V sign / playful) — construida 9-may

**Patrones extraídos:**
- **Recipe peace sign:** index + middle proximal con curl LIGERO o straight, ring + little FUERTE curl (Z positive ~0.3-0.7). Esto deja los 2 dedos extendidos arriba.
- **Brazo levantado moderado:** `rightUpperArm.z = PI*0.583` (más alto que rest 0.40, pero no overhead) → la mano queda a altura de la cara. La X+ leve (0.117) inclina hacia delante.
- **leftLowerArm.z = -PI*0.811** (HUGE!) → cuando el upperArm está cerca de rest, ese Z grande hace que el antebrazo se torsione/redirija. En este caso parece causar que la mano izquierda quede pegada al lado/atrás del cuerpo de forma natural.
- **leftThumbProximal con valores altos en X+Y+Z** (~0.4-0.43) → el pulgar opuesto naturalmente, importante para que la mano "cerrada" se vea como puño relajado y no como tabla.

### Lección global #7 — Peace sign / V sign recipe

```js
// Mano derecha haciendo V sign:
rightIndexProximal:   { x: -PI*0.14, y: -PI*0.32, z: PI*0.21 },  // dedo extendido
rightIndexIntermediate:{ y: -PI*0.63, z: PI*0.11 },               // Y grande = twist invisible
rightMiddleProximal:  { x: -PI*0.24, y: -PI*0.29, z: PI*0.15 },  // dedo extendido
rightMiddleIntermediate:{ y: -PI*0.62, z: PI*0.07 },              // similar middle
rightRingProximal:    { x: -PI*0.22, y: -PI*0.29, z: PI*0.15 },  // ring también?
rightRingIntermediate:{ y: -PI*0.63, z: PI*0.07 },                //
rightLittleProximal:  { z: PI*0.37 },                              // little curl (Z fuerte)
rightLittleIntermediate:{ z: PI*0.71 },                            // little curl extremo
```

> Nota: index, middle Y RING quedan extendidos. Solo little curva. Eso es porque el dedo
> anular es difícil de doblar SOLO sin que el meñique le siga (anatomía humana — los
> tendones del meñique y anular están conectados). La pose lo respeta.

### Lección global #8 — Y axis enorme en intermediate fingers = twist invisible

`indexIntermediate.y = -PI*0.633` (~-114°) parece extremo pero NO bende el dedo —
el dedo se ve recto. Es twist longitudinal del segmento intermedio, invisible.

Esto es **igual al patrón del lowerArm.y** que vimos en la wave. Mismo principio:
para joints "after rotation", Y se vuelve longitudinal.

---

## (Próximas poses se añaden aquí conforme las construyas)

### `<próxima_pose>` — pendiente
_..._
