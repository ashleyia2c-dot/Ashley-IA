"""
legal_content.py — Privacy Policy + Terms of Service para Ashley.

Requisitos legales para vender en Lemon Squeezy / aplicar GDPR. Estos textos
están diseñados para ser accurate respecto a lo que Ashley REALMENTE hace
(privacy-first, datos en tu PC, BYOK con providers terceros), no genéricos
copy-paste de internet.

ESTOS TEXTOS DEBEN SER REVISADOS POR ABOGADO antes del lanzamiento público.
Son un punto de partida sólido pero no sustituyen consejo legal local.

Ashley es una app desktop, no SaaS. Los datos del user viven en su PC en
%APPDATA%\\Ashley\\data\\. La única información que sale del PC es:
  1. Mensajes que el user envía al LLM (xAI / OpenRouter / Ollama) — BYOK
  2. License key contra Lemon Squeezy API (validate/activate/deactivate)
  3. Cloudflare Quick Tunnel para acceso móvil (opcional, off por defecto)
  4. ElevenLabs/Kokoro/VoiceVox para TTS (opcional)
  5. Auto-update check contra GitHub Releases (sin datos personales)

Estructura: cada idioma tiene `privacy_policy_md` y `terms_of_service_md`,
ambos como strings markdown listos para `rx.markdown()`.
"""

# ═══════════════════════════════════════════════════════════════════════════
#  PRIVACY POLICY + TERMS OF SERVICE — ENGLISH (legal master)
# ═══════════════════════════════════════════════════════════════════════════

_PRIVACY_EN = """## Privacy Policy

**Last updated: 2026-05-10**

Ashley ("the app") is a desktop AI companion that runs on your computer. We
designed Ashley with privacy as a core principle: your data lives on YOUR PC,
not on our servers.

### What we collect

**On your PC (never sent to us):**
- Chat history with Ashley
- Facts she remembers about you
- Diary entries she writes
- Voice settings, language preferences, achievements
- Your API keys for the LLM providers you use

These are stored as JSON files in `%APPDATA%\\Ashley\\data\\` (Windows). You
can read them, back them up, or delete them at any time.

**Sent to third parties (only when you use the relevant feature):**
- **LLM providers (xAI, OpenRouter, Ollama)**: chat messages and system
  prompts, sent using YOUR own API key (BYOK — Bring Your Own Key). These
  providers have their own privacy policies. Ashley uses xAI by default; you
  can switch in Settings.
- **Lemon Squeezy**: your license key, sent only during activation /
  validation / deactivation, to verify your purchase. We send no other
  personal data.
- **ElevenLabs / Kokoro / VoiceVox** (optional, only if you enable
  premium voice): the text Ashley speaks, sent to the TTS provider.
- **Cloudflare Quick Tunnel** (optional, only if you enable mobile access):
  a temporary public URL to reach your PC from your phone. Tunnel is
  ephemeral and unauthenticated except for our internal pairing token.
- **GitHub Releases**: anonymous version-check requests for auto-update.
  No personal data.

### What we DON'T do

- We do not run any analytics, telemetry, or crash reporting service.
- We do not collect, transmit, or store your conversations on any server we
  control.
- We do not sell, share, or monetize your data in any way.
- We do not use your conversations to train AI models. (Note: the LLM
  provider you choose may have its own data usage policy — see theirs.)

### Cookies

Ashley desktop is a native app, not a website, so no cookies are used by
the app itself. The Lemon Squeezy checkout page (which you visit only when
purchasing) may use cookies; see their privacy policy.

### Your rights (GDPR / CCPA)

- **Access**: all your data is in `%APPDATA%\\Ashley\\data\\` — open it any
  time.
- **Deletion**: uninstall the app and delete the data folder, or use
  "Clear all memories" inside the app to wipe Ashley's knowledge of you
  while keeping the app installed.
- **Portability**: the JSON files are human-readable and standard.
- **Correction**: you can edit any of those JSON files manually if you want
  to correct something Ashley remembered wrong.
- **License deactivation**: contact us at hello@ashley-ia.com to deactivate
  your license remotely if you lose access to your PC.

### Children

Ashley is not intended for users under 13. We do not knowingly allow
accounts for minors. If you believe a minor has installed Ashley, please
contact us.

### Changes

We will update this policy as Ashley evolves. The "Last updated" date at
the top reflects the most recent revision. Significant changes will be
announced in-app.

### Contact

Questions, concerns, data deletion requests: **hello@ashley-ia.com**
"""

_TERMS_EN = """## Terms of Service

**Last updated: 2026-05-10**

By installing or using Ashley ("the app"), you agree to these terms. If
you do not agree, please uninstall the app.

### License

Ashley is sold under a one-time perpetual license per device. Your purchase
through Lemon Squeezy grants you the right to install and use the app on
the number of devices specified in your license (typically 3). You can
deactivate a device anytime to free up a slot for another machine.

### Bring Your Own Key (BYOK)

Ashley does not include any LLM API access. To use Ashley, you must
provide your own API key from one of: xAI (Grok), OpenRouter, or a local
Ollama instance. The cost of LLM API usage is your responsibility and
billed by the provider directly. Ashley charges you nothing on top.

### Acceptable use

You agree NOT to:
- Use Ashley to generate content that violates laws of your jurisdiction.
- Reverse-engineer the app to bypass the license validation.
- Resell or redistribute the app installer to others. (Sharing your license
  key with someone else will likely fail since the activation slot is
  device-bound.)
- Use Ashley to harass, deceive, or harm others.

### Disclaimers

Ashley is provided "AS IS" without warranties of any kind. We do not
guarantee:
- That the app will be free of bugs (please report any at the email below).
- That the LLM providers will continue to exist or remain available.
- That responses generated by the LLM will be accurate, appropriate, or
  fit for any particular purpose.

You are responsible for reviewing what Ashley does and says. Do not rely
on Ashley for medical, legal, financial, or other professional advice.

### Limitation of liability

To the maximum extent permitted by law, our total liability for any claims
relating to Ashley is limited to the amount you paid for your license.

### Refunds

We honor refunds within **14 days of purchase**, no questions asked.
Contact hello@ashley-ia.com with your license key. Refunds processed via
Lemon Squeezy in 1-5 business days.

### Termination

We may revoke a license if you violate these terms. You can stop using
Ashley anytime by uninstalling.

### Governing law

These terms are governed by the laws of [JURISDICTION TO BE FILLED IN BY
THE SELLER]. Disputes will be resolved in the courts of that jurisdiction.

### Contact

Questions, refund requests, support: **hello@ashley-ia.com**
"""


# ═══════════════════════════════════════════════════════════════════════════
#  PRIVACY POLICY + TERMS OF SERVICE — ESPAÑOL
# ═══════════════════════════════════════════════════════════════════════════

_PRIVACY_ES = """## Política de Privacidad

**Última actualización: 2026-05-10**

Ashley ("la app") es una compañera AI de escritorio que vive en tu ordenador.
Hemos diseñado Ashley con la privacidad como principio fundamental: tus
datos viven en TU PC, no en nuestros servidores.

### Qué recopilamos

**En tu PC (nunca enviado a nosotros):**
- Historial de chat con Ashley
- Hechos que ella recuerda sobre ti
- Entradas de diario que escribe
- Configuración de voz, idioma, achievements
- Tus API keys de los proveedores LLM que uses

Estos se guardan como archivos JSON en `%APPDATA%\\Ashley\\data\\`
(Windows). Puedes leerlos, hacer backup o borrarlos cuando quieras.

**Enviado a terceros (solo cuando uses la función relevante):**
- **Proveedores LLM (xAI, OpenRouter, Ollama)**: mensajes de chat y prompts
  del sistema, enviados con TU propia API key (BYOK — Bring Your Own Key).
  Estos proveedores tienen sus propias políticas de privacidad. Ashley usa
  xAI por defecto; puedes cambiar en Ajustes.
- **Lemon Squeezy**: tu license key, enviada solo durante activación /
  validación / desactivación para verificar tu compra. No enviamos
  ningún otro dato personal.
- **ElevenLabs / Kokoro / VoiceVox** (opcional, solo si activas voz
  premium): el texto que Ashley habla, enviado al proveedor TTS.
- **Cloudflare Quick Tunnel** (opcional, solo si activas acceso móvil):
  una URL pública temporal para alcanzar tu PC desde tu móvil. El túnel
  es efímero y no autenticado salvo por nuestro pairing token interno.
- **GitHub Releases**: requests anónimas de version-check para auto-update.
  Sin datos personales.

### Lo que NO hacemos

- No corremos analytics, telemetría ni crash reporting.
- No recopilamos, transmitimos ni almacenamos tus conversaciones en
  ningún servidor que controlemos.
- No vendemos, compartimos ni monetizamos tus datos de ninguna forma.
- No usamos tus conversaciones para entrenar modelos de IA. (Nota: el
  proveedor LLM que elijas puede tener su propia política — consulta la
  suya.)

### Cookies

Ashley desktop es una app nativa, no un sitio web, así que no usa cookies.
La página de checkout de Lemon Squeezy (que solo visitas al comprar) puede
usar cookies; consulta su política.

### Tus derechos (RGPD / CCPA)

- **Acceso**: todos tus datos están en `%APPDATA%\\Ashley\\data\\` —
  ábrelo cuando quieras.
- **Borrado**: desinstala la app y borra la carpeta de datos, o usa
  "Borrar todas las memorias" dentro de la app para limpiar lo que Ashley
  sabe de ti sin desinstalar.
- **Portabilidad**: los archivos JSON son legibles y estándar.
- **Rectificación**: puedes editar manualmente esos JSON si quieres
  corregir algo que Ashley recordó mal.
- **Desactivación de licencia**: contacta hello@ashley-ia.com para
  desactivar tu licencia remotamente si pierdes acceso a tu PC.

### Menores

Ashley no está pensada para usuarios menores de 13 años. No permitimos
conscientemente cuentas de menores. Si crees que un menor ha instalado
Ashley, por favor contacta con nosotros.

### Cambios

Actualizaremos esta política conforme Ashley evolucione. La fecha de
"Última actualización" arriba refleja la revisión más reciente. Cambios
significativos se anunciarán dentro de la app.

### Contacto

Preguntas, dudas, peticiones de borrado de datos: **hello@ashley-ia.com**
"""

_TERMS_ES = """## Términos de Servicio

**Última actualización: 2026-05-10**

Al instalar o usar Ashley ("la app"), aceptas estos términos. Si no
estás de acuerdo, por favor desinstala la app.

### Licencia

Ashley se vende bajo una licencia perpetua de pago único por dispositivo.
Tu compra a través de Lemon Squeezy te otorga el derecho a instalar y
usar la app en el número de dispositivos especificados en tu licencia
(típicamente 3). Puedes desactivar un dispositivo en cualquier momento
para liberar un slot para otra máquina.

### Bring Your Own Key (BYOK)

Ashley no incluye acceso a ninguna API de LLM. Para usar Ashley debes
proveer tu propia API key de uno de: xAI (Grok), OpenRouter, o una
instancia local de Ollama. El coste del uso de la API LLM es tu
responsabilidad y lo factura el proveedor directamente. Ashley no te
cobra nada extra.

### Uso aceptable

Aceptas NO:
- Usar Ashley para generar contenido que viole leyes de tu jurisdicción.
- Hacer ingeniería inversa a la app para saltarte la validación de licencia.
- Revender o redistribuir el instalador. (Compartir tu license key con otra
  persona probablemente fallará porque el slot de activación está
  vinculado al dispositivo.)
- Usar Ashley para acosar, engañar o hacer daño a otras personas.

### Disclaimers

Ashley se provee "TAL CUAL" sin garantías de ningún tipo. No garantizamos:
- Que la app esté libre de bugs (por favor reporta cualquier al email de
  abajo).
- Que los proveedores LLM sigan existiendo o disponibles.
- Que las respuestas que genera el LLM sean precisas, apropiadas, o
  adecuadas para ningún propósito particular.

Eres responsable de revisar qué hace y dice Ashley. NO uses Ashley para
consejos médicos, legales, financieros o de cualquier otra naturaleza
profesional.

### Limitación de responsabilidad

En la medida máxima permitida por la ley, nuestra responsabilidad total
por cualquier reclamo relacionado con Ashley se limita al importe que
pagaste por tu licencia.

### Reembolsos

Honramos reembolsos dentro de los **14 días desde la compra**, sin hacer
preguntas. Contacta hello@ashley-ia.com con tu license key. Los
reembolsos se procesan vía Lemon Squeezy en 1-5 días hábiles.

### Terminación

Podemos revocar una licencia si violas estos términos. Puedes dejar de
usar Ashley en cualquier momento desinstalando.

### Ley aplicable

Estos términos se rigen por las leyes de [JURISDICCIÓN A RELLENAR POR EL
VENDEDOR]. Las disputas se resolverán en los tribunales de esa
jurisdicción.

### Contacto

Preguntas, reembolsos, soporte: **hello@ashley-ia.com**
"""


# ═══════════════════════════════════════════════════════════════════════════
#  Dispatcher
# ═══════════════════════════════════════════════════════════════════════════

# v0.19.7 — Por ahora solo EN/ES. FR/JA/DE/RU/KO caerán a EN como fallback.
# Traducción a los demás idiomas: tarea futura (legal review primero).
PRIVACY_POLICY = {
    "en": _PRIVACY_EN,
    "es": _PRIVACY_ES,
}

TERMS_OF_SERVICE = {
    "en": _TERMS_EN,
    "es": _TERMS_ES,
}


def get_privacy_policy(lang: str) -> str:
    """Devuelve el markdown de la privacy policy en el idioma dado.
    Fallback a EN para idiomas sin traducción."""
    return PRIVACY_POLICY.get((lang or "en")[:2].lower(), _PRIVACY_EN)


def get_terms_of_service(lang: str) -> str:
    """Devuelve el markdown de los terms of service en el idioma dado.
    Fallback a EN para idiomas sin traducción."""
    return TERMS_OF_SERVICE.get((lang or "en")[:2].lower(), _TERMS_EN)
