# Wake word — modelo en runtime

Esta carpeta está vacía en el repo. Recibe el modelo entrenado en runtime.

## Archivos esperados

- `ashley.onnx` — modelo de detección (~16 KB)
- `ashley.onnx.data` — pesos del modelo (~410 KB)

## Cómo poblarla

1. Entrenar el modelo:
   ```cmd
   cd ../../wake_word_training
   venv\Scripts\activate
   python scripts\04_train.py
   ```

2. Copiar a esta carpeta:
   ```cmd
   python scripts\06_install_in_ashley.py
   ```

   Eso copia `output/ashley.onnx` aquí + instala las deps de inferencia
   (`openwakeword`, `sounddevice`) en el venv principal de Ashley.

## ¿Por qué no commiteamos el .onnx?

Los binarios se regeneran con cada training y hacen el git history
pesado. El installer (`electron-builder`) sí los bundlea si están
presentes en el momento del build.

Cuando hagas un release, asegúrate de:
1. Tener el modelo entrenado en su sitio (corre `04_train.py` + `06_install_in_ashley.py`)
2. Build el installer (`cd electron && npm run build`)
