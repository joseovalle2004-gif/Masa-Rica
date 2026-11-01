
document.addEventListener("DOMContentLoaded", () => {
    const contenido = document.getElementById("ventas-contenido");

    if (!contenido) {
        return;
    }

    const INTERVALO_ACTUALIZACION = 15000;

    let actualizando = false;
    let contenidoAnterior = "";

    async function actualizarVentas() {
        if (actualizando || document.hidden) {
            return;
        }

        actualizando = true;

        try {
            const respuesta = await fetch(window.location.href, {
                method: "GET",
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                },
                cache: "no-store",
                credentials: "same-origin"
            });

            if (!respuesta.ok) {
                throw new Error(
                    `Error al consultar ventas: ${respuesta.status}`
                );
            }

            const html = await respuesta.text();

            const documento = new DOMParser().parseFromString(
                html,
                "text/html"
            );

            const nuevoContenido = documento.getElementById(
                "ventas-contenido"
            );

            if (!nuevoContenido) {
                return;
            }

            const nuevoHTML = nuevoContenido.innerHTML;

            if (nuevoHTML === contenidoAnterior) {
                return;
            }

            contenidoAnterior = nuevoHTML;

            const filtrosActuales = contenido.querySelector(
                "#filtros-ventas"
            );

            const filtrosNuevos = nuevoContenido.querySelector(
                "#filtros-ventas"
            );

            if (filtrosActuales && filtrosNuevos) {
                filtrosNuevos.replaceWith(
                    filtrosActuales.cloneNode(true)
                );
            }

            contenido.innerHTML = nuevoContenido.innerHTML;

            document.dispatchEvent(
                new CustomEvent("operia:ventas-actualizadas")
            );

        } catch (error) {
            console.error(
                "No se pudieron actualizar las ventas:",
                error
            );

        } finally {
            actualizando = false;
        }
    }

    setInterval(
        actualizarVentas,
        INTERVALO_ACTUALIZACION
    );

    document.addEventListener(
        "visibilitychange",
        () => {
            if (!document.hidden) {
                actualizarVentas();
            }
        }
    );
});
