/**
 * prebuild.js — Forzar un build fresco del frontend antes de empaquetar.
 *
 * Garantiza que el installer NUNCA salga con un build de frontend stale
 * respecto al código Python actual. Sin esto, un dev que se olvidara de
 * ejecutar `reflex export` manualmente antes de `npm run build` podría
 * distribuir un .exe donde la UI no refleja features nuevas (ej. pill
 * "Noticias" invisible en v0.13.3 antes del fix).
 *
 * Se ejecuta automáticamente como `prebuild-frontend` desde el script
 * `build` y `release` en package.json (ambos lo encadenan vía `&&`).
 *
 * Side effect: actualiza .web/build/client/ con el build reciente. Ese
 * directorio se incluye en extraResources, así que lo que aquí se
 * genere es exactamente lo que recibe el user.
 */
const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

const ROOT = path.resolve(__dirname, '..');

// v0.19.3 — usamos python.exe -m reflex (no reflex.exe, que tiene path
// absoluto baked-in al python que hizo el pip install).
function resolvePythonExe() {
  const isWin = process.platform === 'win32';
  const embedPy = isWin
    ? path.join(ROOT, 'python-embed', 'python.exe')
    : path.join(ROOT, 'python-embed', 'bin', 'python');
  if (fs.existsSync(embedPy)) return embedPy;
  const venvPy = isWin
    ? path.join(ROOT, 'venv', 'Scripts', 'python.exe')
    : path.join(ROOT, 'venv', 'bin', 'python');
  return venvPy;
}

const PYTHON_EXE = resolvePythonExe();

if (!fs.existsSync(PYTHON_EXE)) {
  console.error(`[prebuild] Cannot find python.exe at ${PYTHON_EXE}`);
  console.error('[prebuild] No has corrido el setup de Python embeddable.');
  console.error('[prebuild] Run: python tools/setup_python_embed.py');
  console.error('[prebuild] (Alternativa legacy: python -m venv venv && venv/Scripts/pip install -r requirements.txt)');
  process.exit(1);
}

// Guardamos el zip en un dir temporal — no lo usamos, electron-builder
// toma directamente los archivos de .web/build/client/. Reflex SIEMPRE
// escribe ahí cuando hace export; el zip es solo un efecto secundario
// que no podemos saltar del CLI actual.
const exportDir = path.join(os.tmpdir(), 'ashley-prebuild-export');
try { fs.mkdirSync(exportDir, { recursive: true }); } catch {}

console.log('[prebuild] Forcing fresh frontend build — no stale assets in installer.');
console.log('[prebuild] This takes ~10s on cold cache, ~3s on warm.');
try {
  // v0.19.3 — `python -m reflex export` en lugar de `reflex export` para
  // evitar el shim con path absoluto baked-in.
  execSync(`"${PYTHON_EXE}" -m reflex export --frontend-only --zip-dest-dir "${exportDir}"`, {
    cwd: ROOT,
    stdio: 'inherit',
  });
} catch (e) {
  console.error('\n[prebuild] ❌ Frontend build FAILED.');
  console.error('[prebuild] Aborting installer — we WILL NOT ship a release with stale UI.');
  console.error('[prebuild] Check the error above and fix before retrying.');
  process.exit(1);
}

const builtIndex = path.join(ROOT, '.web', 'build', 'client', 'index.html');
if (!fs.existsSync(builtIndex)) {
  console.error('[prebuild] ❌ Build succeeded but index.html missing — something is broken.');
  process.exit(1);
}

// Limpiar el zip temporal (no lo necesitamos, .web/build/client/ ya quedó bien)
try {
  fs.rmSync(exportDir, { recursive: true, force: true });
} catch {}

console.log('[prebuild] ✅ Frontend build complete. electron-builder can now package safely.');
