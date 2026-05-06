package com.ashleyia.mobile;

import android.os.Bundle;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;

import com.getcapacitor.BridgeActivity;

/**
 * MainActivity custom para Ashley Mobile.
 *
 * v0.18.2 — sobreescribe el WebChromeClient del Capacitor WebView para
 * delegar permisos de cámara/audio al sistema Android. Sin esto,
 * navigator.mediaDevices.getUserMedia() falla con "Permission denied"
 * sin siquiera mostrar el dialog del sistema.
 *
 * Necesario para que el QR scanner funcione (usa getUserMedia para
 * acceder a la cámara trasera).
 *
 * El grant es automático porque la app es nuestra (no carga contenido
 * externo arbitrario que pudiera intentar acceder a la cámara). Si en
 * el futuro la app cargara contenido externo via WebView, habría que
 * filtrar las request.getResources() o pedir confirmación al user.
 */
public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Reemplazar el WebChromeClient default por uno que delegue
        // permisos de hardware (cámara + mic) al sistema.
        bridge.getWebView().setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        // Otorgar los permisos solicitados (camera, audio).
                        // El sistema Android ya pidió permission al user
                        // cuando la app se instaló si tiene CAMERA en el
                        // manifest. Aquí solo concedemos el WebView grant.
                        request.grant(request.getResources());
                    }
                });
            }
        });
    }
}
