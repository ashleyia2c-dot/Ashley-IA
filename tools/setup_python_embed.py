"""setup_python_embed.py — Crea un Python portable autocontenido para bundlear con Ashley.

Por qué existe: el approach de `python -m venv venv` + bundlear venv falla en
PCs ajenos al de build. Los `python.exe`/`reflex.exe` dentro del venv son shims
que leen `pyvenv.cfg` para encontrar el Python "home" — y ese path es absoluto
al disco original (ej. `C:\\hostedtoolcache\\windows\\Python\\3.12.10\\x64\\python.exe`
en GitHub Actions, o `C:\\Users\\Tú\\Desktop\\proyecto\\venv` en local). En el
PC del comprador ese path NO existe → "No Python at..." → backend muere.

Solución: usar la distribución **Python embeddable** de python.org. Es un zip
pre-empaquetado con `python.exe`, `python312.dll`, stdlib comprimida, y CERO
referencias a paths absolutos. Lo extraemos a `python-embed/`, lo configuramos
para que pueda importar de `Lib/site-packages/` (por defecto el embeddable los
ignora), instalamos pip + requirements directos a esa carpeta, y bundleamos
TODO en el installer.

Resultado: una carpeta `python-embed/` plug-and-play que funciona en cualquier
Windows x64 sin Python instalado.

Uso:
    python tools/setup_python_embed.py

Idempotente: si python-embed/ ya existe con la marker file correcta, hace skip.
Para forzar rebuild: --force.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

# Forzar UTF-8 en stdout — sin esto, en Windows con cp1252 cualquier print
# con caracteres no-ASCII (→ ✓ etc) crashea con UnicodeEncodeError.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ─────────────────────────────────────────────────────────────────
# Versión Python a embeddear. DEBE coincidir con la versión que
# usamos para desarrollo local + en .github/workflows/release.yml
# para que requirements.txt instale wheels compatibles.
# ─────────────────────────────────────────────────────────────────
PYTHON_VERSION = "3.12.10"
EMBED_URL = (
    f"https://www.python.org/ftp/python/{PYTHON_VERSION}/"
    f"python-{PYTHON_VERSION}-embed-amd64.zip"
)
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"

ROOT = Path(__file__).resolve().parent.parent
EMBED_DIR = ROOT / "python-embed"
DOWNLOADS = ROOT / ".cache" / "python-embed-downloads"
MARKER = EMBED_DIR / ".setup-complete-v1"
REQUIREMENTS = ROOT / "requirements.txt"


def log(msg: str) -> None:
    print(f"[setup-embed] {msg}", flush=True)


def download(url: str, dest: Path) -> None:
    """Descarga url → dest si no existe ya. Skip si está cacheado."""
    if dest.exists() and dest.stat().st_size > 0:
        log(f"  cache hit: {dest.name}")
        return
    log(f"  downloading {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    urllib.request.urlretrieve(url, tmp)
    tmp.rename(dest)
    log(f"  saved to {dest} ({dest.stat().st_size / 1e6:.1f} MB)")


def extract_embed(zip_path: Path, dest: Path) -> None:
    """Extrae el embeddable zip + crea Scripts/ y Lib/site-packages/."""
    log(f"extracting {zip_path.name} → {dest}")
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(dest)
    # Carpetas que necesitamos para pip + entry points
    (dest / "Scripts").mkdir(exist_ok=True)
    (dest / "Lib" / "site-packages").mkdir(parents=True, exist_ok=True)


def patch_pth_file(embed_dir: Path) -> None:
    """Habilita import site para que `Lib/site-packages` se busque automaticamente.

    El embeddable trae un `python3XX._pth` con `import site` COMENTADO. Eso
    bloquea la búsqueda automática de site-packages. Lo descomentamos +
    añadimos las rutas que pip va a usar.
    """
    pth_files = list(embed_dir.glob("python*._pth"))
    if not pth_files:
        raise RuntimeError(f"No encontré python*._pth en {embed_dir}")
    pth = pth_files[0]
    log(f"patching {pth.name}")
    content = pth.read_text(encoding="utf-8")
    # Descomenta `import site` si está comentado
    content = content.replace("#import site", "import site")
    # Asegura que Lib\site-packages y Scripts estén en sys.path
    extra_paths = ["Lib\\site-packages", "Scripts", ".."]
    for p in extra_paths:
        if p not in content:
            content += f"\n{p}\n"
    pth.write_text(content, encoding="utf-8")


def bootstrap_pip(embed_dir: Path) -> None:
    """Instala pip + setuptools + wheel en el embeddable usando get-pip.py.

    NOTA: get-pip.py por defecto solo instala pip (no setuptools ni wheel).
    Pero muchos paquetes PEP 517 fallan al hacer source build sin setuptools
    (vimos esto en CI: BackendUnavailable: Cannot import 'setuptools.build_meta').
    Por eso le pasamos explícitamente setuptools + wheel.
    """
    get_pip = DOWNLOADS / "get-pip.py"
    download(GET_PIP_URL, get_pip)
    python_exe = embed_dir / "python.exe"
    log("bootstrapping pip + setuptools + wheel")
    subprocess.run(
        [
            str(python_exe), str(get_pip),
            "--no-warn-script-location",
            "setuptools", "wheel",  # ← extras explícitos para PEP 517 builds
        ],
        check=True,
    )


def install_requirements(embed_dir: Path) -> None:
    """Instala todo de requirements.txt al site-packages del embeddable."""
    python_exe = embed_dir / "python.exe"
    log("installing requirements.txt — esto tarda 2-5 min")
    subprocess.run(
        [
            str(python_exe), "-m", "pip", "install",
            "--no-warn-script-location",
            "--upgrade",
            "-r", str(REQUIREMENTS),
        ],
        check=True,
    )


def verify(embed_dir: Path) -> None:
    """Sanity check: importar reflex_companion debe funcionar."""
    python_exe = embed_dir / "python.exe"
    log("verifying reflex import works")
    # NOTE: reflex >=0.8 ya no expone __version__ public via lazy loader,
    # así que no podemos imprimirla. Suficiente con que el import no crashee.
    result = subprocess.run(
        [
            str(python_exe), "-c",
            "import reflex_companion.reflex_companion; print('IMPORT OK')",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        log("VERIFICATION FAILED:")
        log("STDOUT: " + result.stdout)
        log("STDERR: " + result.stderr)
        raise SystemExit(1)
    log(f"  {result.stdout.strip()}")
    # También verificar que reflex.exe existe (el script entry-point)
    reflex_exe = embed_dir / "Scripts" / "reflex.exe"
    if not reflex_exe.exists():
        raise SystemExit(f"reflex.exe entry point missing at {reflex_exe}")
    log(f"  reflex.exe found at {reflex_exe}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true",
        help="Borrar python-embed/ existente y reinstalar todo desde cero",
    )
    args = parser.parse_args()

    if MARKER.exists() and not args.force:
        log(f"python-embed ya está montado (marker: {MARKER.name})")
        log("usa --force para reinstalar desde cero")
        return

    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    embed_zip = DOWNLOADS / f"python-{PYTHON_VERSION}-embed-amd64.zip"

    download(EMBED_URL, embed_zip)
    extract_embed(embed_zip, EMBED_DIR)
    patch_pth_file(EMBED_DIR)
    bootstrap_pip(EMBED_DIR)
    install_requirements(EMBED_DIR)
    verify(EMBED_DIR)

    # Marker para que invocaciones futuras del script hagan skip.
    MARKER.write_text(
        f"setup-complete\npython-version: {PYTHON_VERSION}\n",
        encoding="utf-8",
    )
    log(f"DONE. python-embed/ listo en {EMBED_DIR}")
    log(f"size: {sum(f.stat().st_size for f in EMBED_DIR.rglob('*') if f.is_file()) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
