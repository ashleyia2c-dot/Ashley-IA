# Releasing Ashley

Pasos para construir el installer y publicar una nueva versión.

## 1. Asegúrate de que `main` está limpia y al día

```bash
cd C:\Users\Mister Squishi\Desktop\reflex-companion
git checkout main
git pull
git status  # debe decir "nothing to commit, working tree clean"
```

## 2. Verifica que los tests pasan

```bash
venv\Scripts\python.exe -m pytest tests/
```

Debe decir `X passed`.

## 3. Verifica la versión

El número en `electron/package.json` debe coincidir con el tag que vas a crear.

```bash
grep '"version"' electron/package.json
```

## 4. Pre-build del frontend prod

Esto genera `.web/build/` con los assets compilados que luego se incluyen en el installer, para que el user no tenga que esperar un rebuild de Vite en la primera apertura.

```bash
cd C:\Users\Mister Squishi\Desktop\reflex-companion
venv\Scripts\reflex.exe run --env prod --frontend-only
```

Deja que arranque hasta que diga "App Running". Eso significa que `.web/build/` ya está generado. Ciérralo con Ctrl+C.

**Nota:** si ya existe `.web/build/` de un launch anterior, puedes saltar este paso. Se puede verificar:

```bash
ls .web/build/client/
```

Si hay archivos, está OK.

## 5. Build del installer

```bash
cd electron
npm run build
```

Esto tarda unos minutos. Copia `venv/`, `reflex_companion/`, `assets/`, `.web/` (sin `node_modules`) al bundle de Electron vía `extraResources`. El resultado:

- `electron/dist/Ashley-Setup-X.Y.Z.exe` (~200 MB)
- `electron/dist/Ashley-Setup-X.Y.Z.exe.blockmap` (para el auto-updater)

## 6. Test local del installer

**IMPORTANTE** antes de publicar: prueba el installer en una VM limpia (sin Python instalado, sin reflex-companion en Desktop). Si no tienes VM a mano, como mínimo:

1. Instala el `.exe` generado
2. Click en el shortcut de Ashley que crea NSIS (menú Inicio)
3. Verifica que arranca sin errores
4. Verifica que puedes mandar mensaje y Ashley responde
5. Verifica que no abre tu venv de dev (solo el del installer)

Si algo falla, mira `%APPDATA%\Ashley\logs\main.log` — ahí sale `WARNING: packaged app but no venv in ...` si el bundling falló.

## 7. Crear tag + push

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

## 8. Crear Release en GitHub

Con `gh` CLI:

```bash
gh release create vX.Y.Z electron/dist/Ashley-Setup-X.Y.Z.exe electron/dist/Ashley-Setup-X.Y.Z.exe.blockmap --title "vX.Y.Z" --notes "Release notes aquí"
```

O manualmente en github.com/ashleyia2c-dot/Ashley-IA/releases/new.

**Crítico**: el archivo `.blockmap` debe subirse junto al `.exe`. Es lo que usa electron-updater para calcular diffs y hacer updates delta (pequeños) en vez de re-descargar todo.

## 9. Verificar auto-update

Abre tu Ashley instalada (la vieja). Debería detectar la nueva release dentro de 1 minuto y preguntarte si quieres actualizar.

## 10. Notas de cada release

Registra lo que cambió en la sección "Release notes" de GitHub. Para v0.10.0+:

- Primera release con **installer self-contained** (incluye venv + source + frontend compilado)
- Startup mucho más rápido con `reflex run --env prod`
- [incluir los fixes de este release]

## Troubleshooting

### "No encuentro reflex.exe" al abrir Ashley instalada

- Verifica que `extraResources` del electron-builder incluye `venv` correctamente
- Abre `%APPDATA%\Ashley\logs\main.log` y busca `WARNING: packaged app but no venv`
- Compara `electron/dist/win-unpacked/resources/venv/Scripts/reflex.exe` — debe existir

### Installer crece a >1 GB

- Verifica que los filter excluyen `__pycache__`, `*.pyc`, `tests/`
- Considera excluir también `Lib/site-packages/*/tests/` si los paquetes lo traen

### Antivirus marca el installer como sospechoso

- Normal para Electron apps sin certificado de firma digital
- A largo plazo: comprar cert de firma (~€150/año con EV cert desde SSL.com o similar)
- MVP: indicar en la landing "click 'more info' → 'run anyway' si Windows lo bloquea"
