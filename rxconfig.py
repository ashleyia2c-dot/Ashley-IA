import reflex as rx

# Puertos forzados fuera del rango típicamente reservado por Windows/Hyper-V
# (Hyper-V suele reservar rangos bajos como 3000-3050, 8000-8050).
# Electron lee estos puertos vía main.js para conectar al backend correcto.
config = rx.Config(
    app_name="reflex_companion",
    frontend_port=17300,
    backend_port=17800,
    # Quitamos el badge "Built with Reflex" de la esquina — no queremos
    # marca del framework visible en un producto comercial.
    show_built_with_reflex=False,
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ]
)