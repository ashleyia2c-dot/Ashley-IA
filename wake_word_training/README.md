# Ashley Wake Word Training

Training pipeline para entrenar un detector de wake word custom para "Ashley"
usando OpenWakeWord. El modelo final (~5 MB) se empaqueta con la app y permite
que Ashley te oiga sin tocar nada.

## Hardware

GPU: RTX 5060 (Blackwell, 8 GB VRAM, CUDA 13.2)
Tiempo de training estimado: 3-4 horas
Disco usado durante training: ~10-15 GB (limpiable después)

## Estructura

```
wake_word_training/
├── README.md                  # este archivo
├── requirements.txt           # deps del training
├── setup.bat                  # script de instalación one-shot
├── ashley.yaml                # generado por 04_train.py
├── data/
│   ├── validation_set_features.npy  # auto-descargado (~250 MB)
│   ├── rir/                   # room impulse responses (auto + manual)
│   ├── background/            # background noise (auto + manual)
│   ├── positive/              # OPCIONAL — samples extra grabados
│   └── negative/              # OPCIONAL — samples extra de "no ashley"
├── piper-sample-generator/    # auto-clonado por 04_train.py
├── scripts/
│   ├── 01_generate_positive.py   # OPCIONAL — más samples extra con piper
│   ├── 02_download_negative.py   # OPCIONAL — descargar negativos extra
│   ├── 03_augment.py             # OPCIONAL — augmentation manual
│   ├── 04_train.py               # PRINCIPAL — wrapper de openwakeword.train
│   └── 05_test.py                # test con audio real grabado por ti
└── output/
    └── ashley.tflite          # modelo final (post-training)
```

## Flujo recomendado (simple)

OpenWakeWord ya hace generación + augmentation + training internamente. Por
tanto el flujo "feliz" es:

```cmd
cd wake_word_training
venv\Scripts\activate
python scripts/04_train.py     # genera datos + entrena (3-4 h)
python scripts/05_test.py      # mide FRR y FAR con tu mic
```

Si los números son malos, ahí entran los scripts opcionales 01-03.

## Fases

### 1. Setup ambiente (una vez, ~15-30 min con descarga de PyTorch+TF)

**IMPORTANTE para RTX 5060 / 5070 / 5080 / 5090 (Blackwell, sm_120)**:
PyTorch *stable* (cu126/cu128) NO tenía sm_120 a fecha 2026-04. Hay que usar
**PyTorch nightly** o esperar release con soporte oficial.

```cmd
cd wake_word_training
python -m venv venv
venv\Scripts\activate
pip install --upgrade pip

REM PyTorch NIGHTLY con CUDA 12.8 (única build que tiene kernels sm_120 hoy)
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128

REM Resto de deps (openwakeword + piper-tts + tensorflow + audio libs)
pip install -r requirements.txt

REM Verificar que CUDA funciona
python -c "import torch; print('CUDA:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU only')"
```

Output esperado:
```
CUDA: True
Device: NVIDIA GeForce RTX 5060
```

**Si tienes una GPU más vieja (RTX 30/40, Hopper)**: PyTorch stable funciona.
Reemplaza el comando por:
```cmd
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
```

**Deps transitivas que NO están en `requirements.txt` pero las necesita el
training de openwakeword** (instala con `pip install`):
```
torchinfo torchmetrics pyyaml mutagen acoustics
pronouncing torch_audiomentations speechbrain
"scipy<1.15"   # acoustics rompe con scipy 1.17 (sph_harm fue removido)
```

### 2. Training (~3-4 h en RTX 5060)

```cmd
python scripts/04_train.py
```

El script hace TODO automáticamente:
1. Verifica GPU + deps
2. Clona `piper-sample-generator` (lo necesita openwakeword para TTS)
3. Descarga validation features (~250 MB)
4. Crea `data/rir/` y `data/background/` si faltan
5. Genera `ashley.yaml` con la config
6. Lanza `python -m openwakeword.train --training_config ashley.yaml
                                       --generate_clips --augment_clips --train_model`

Lo cual a su vez:
- Genera ~4000 audios sintéticos diciendo "ashley" en distintas voces (Piper)
- Genera ~4000 audios adversariales ("Asher", "ashling", "ashtray"...) — esto
  es CRÍTICO para tener bajo False Accept Rate
- Aplica augmentation con RIR + background
- Computa features
- Entrena un modelo DNN
- Convierte a ONNX → TFlite

Output: `output/ashley/ashley.tflite`

**Nota sobre RIR + background**: si `data/rir/` y `data/background/` están
vacíos, el augmentation hará lo que pueda pero la calidad del modelo bajará.
Para training de calidad, descarga manualmente:
- RIR: https://www.openslr.org/26/ (Aachen IR Database, ~1 GB)
- Background: https://github.com/karolpiczak/ESC-50 (~600 MB)

Y mete los `.wav` en `data/rir/` y `data/background/` antes de correr el script.

### 3. Testing real (~30 min — necesita mic)

```cmd
python scripts/05_test.py
```

Te pide grabar 30 muestras diciendo "ashley" en distintos contextos y mide:
- **False Reject Rate (FRR)**: % de veces que NO te oye → debe ser <5%
- **False Accept Rate (FAR)**: activaciones espontáneas con TV/música/
  conversación de fondo. Debe ser <1 evento/hora.

Si los números son malos, iteramos:
- **FRR alto**: añade más positivos en `data/positive/` (graba tu voz, usa
  `01_generate_positive.py` para más TTS variantes) y vuelve a correr `04_train.py`
- **FAR alto**: añade más negativos similares en `data/negative/` y aumenta
  `custom_negative_phrases` en `ashley.yaml`

### 4. Empaquetar en Ashley

Una vez los números de FRR/FAR son OK, **copia el `.onnx`** (preferido) a:
```
reflex_companion/wake_word/ashley.onnx
```

¿Por qué `.onnx` en vez de `.tflite`? Ashley app ya tiene `onnxruntime`
instalado (lo trae faster-whisper). Usar `.onnx` significa que el bundle
adicional para wake word es solo ~10 MB (openwakeword + sounddevice). Si
usaras `.tflite` tendrías que añadir `tflite_runtime` (~2 MB extra). Igual
es viable, pero `.onnx` es más simple.

Después conectarlo al background loop de Ashley:
```python
from reflex_companion.wake_word import WakeWordDetector

det = WakeWordDetector(model_path="reflex_companion/wake_word/ashley.onnx")
det.start(callback=lambda score: state.start_recording_from_wake_word())
```

(El módulo `reflex_companion/wake_word.py` ya está scaffolded — ver el
docstring del módulo para los pasos de integración con State y UI.)

## Scripts opcionales (01-03)

OpenWakeWord ya genera/aumenta sus propios samples. Los scripts 01-03 son
útiles **sólo si**:

- **`01_generate_positive.py`**: querés añadir muestras adicionales con
  ajustes específicos (más voces masculinas, prosodias custom, etc.) que
  complementen las que genera openwakeword internamente.

- **`02_download_negative.py`**: querés añadir un dataset MUSAN/CommonVoice
  para tener negativos del mundo real (TV, música, conversación) que
  complementen los adversariales sintéticos.

- **`03_augment.py`**: querés un control más fino del augmentation (ej:
  generar 10 variantes por sample en vez de 1).

Estos scripts producen `.wav` en `data/positive/`, `data/negative/`,
`data/augmented/`. OpenWakeWord NO los usa automáticamente — para que entren
en el training tendrías que añadirlos a `feature_data_files` en `ashley.yaml`
y precomputar sus features con `compute_features_from_generator`. Para una
primera iteración, dejalo en blanco y deja que openwakeword haga su gen
sintética sola.

## Estado

- [x] Fase 1: setup ambiente
- [ ] Fase 2: training (`scripts/04_train.py`)
- [ ] Fase 3: testing (`scripts/05_test.py`)
- [ ] Fase 4: integración en Ashley

## Costes / Riesgos

- **Disco**: ~10-15 GB durante training (audios generados + features). Limpiable
  después borrando `output/ashley/positive_train/` etc., dejando sólo el .tflite.
- **Tiempo de PC bloqueado**: ~3-4 horas con la GPU al 100% durante training.
- **Quality risk**: si `data/rir/` y `data/background/` están vacíos, FAR puede
  ser alto. Mitigable descargando los datasets recomendados arriba.
- **API drift**: openwakeword 0.6+ usa la API basada en YAML config descrita
  aquí. Si una versión futura cambia la API de `openwakeword.train`,
  `04_train.py` puede fallar y habría que ajustar al nuevo patrón.
