package com.ashleyia.mobile;

import android.os.Bundle;
import android.webkit.PermissionRequest;

import com.getcapacitor.BridgeActivity;
import com.getcapacitor.BridgeWebChromeClient;

/**
 * MainActivity custom para Ashley Mobile.
 *
 * v0.18.2 — extiende el BridgeWebChromeClient de Capacitor (no WebChromeClient
 * default de Android) y solo override onPermissionRequest. Esto preserva
 * TODO lo que Capacitor hace por defecto (console.log, file chooser,
 * fullscreen video, prompt dialogs, etc.) y solo cambia el comportamiento
 * de permission requests para conceder grant automático.
 *
 * Bug que arregla: navigator.mediaDevices.getUserMedia() del QR scanner
 * fallaba o se colgaba porque Capacitor no concedía el permiso al WebView
 * aunque CAMERA estuviera en el AndroidManifest.
 *
 * Versión anterior reemplazaba el WebChromeClient entero — eso rompía el
 * flujo de permisos nativos de Capacitor y la promise quedaba colgada.
 */
public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // EXTENDER el chrome client de Capacitor, NO reemplazarlo entero.
        bridge.getWebView().setWebChromeClient(new BridgeWebChromeClient(bridge) {
            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                // Auto-grant para hardware (cámara + audio). El sistema Android
                // ya concedió el permiso a la app cuando se instaló (con CAMERA
                // en el manifest). Aquí solo concedemos el grant del WebView
                // al JS (sin esto, getUserMedia falla con "Permission denied"
                // sin siquiera mostrar el dialog).
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        request.grant(request.getResources());
                    }
                });
            }
        });
    }
}
