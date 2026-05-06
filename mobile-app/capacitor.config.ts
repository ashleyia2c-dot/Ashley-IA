/// <reference types="@capacitor/cli" />

import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.ashleyia.mobile',
  appName: 'Ashley',
  webDir: 'www',

  // El APK contiene los assets de la PWA bundleados (offline-first).
  // Las llamadas /api/* van a la URL configurada por el user (su PC LAN
  // o Tailscale). El webDir 'www' se rellena por scripts/sync-assets.js
  // copiando assets/mobile/* del repo Reflex.

  android: {
    // Permite tráfico HTTP plano (no solo HTTPS) — necesario porque
    // el PC del user usa HTTP en LAN. Sin esto Android bloquea por
    // seguridad las conexiones HTTP.
    allowMixedContent: true,
    // Captura back button en Android para navegación dentro del app
    captureInput: true,
    // No usar WebView en modo debuggable en producción
    webContentsDebuggingEnabled: false,
  },

  // Server config — vacío, el app carga 'www' desde el bundle local.
  // Si quisieras cargar desde URL remota, configurarías server.url aquí.
  server: {
    androidScheme: 'http',
  },

  // Plugins que el app puede usar (camera para QR scanning,
  // preferences para guardar config, app para lifecycle)
  plugins: {
    Camera: {
      // permitidos: 'camera' = solo cámara, no galería
      permissions: ['camera'],
    },
  },
};

export default config;
