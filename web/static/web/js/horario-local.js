
document.addEventListener("DOMContentLoaded", function () {
    const etiqueta = document.getElementById("estado-local-etiqueta");
    const detalle = document.getElementById("estado-local-detalle");
    const boton = document.getElementById("estado-local-toggle");
    const desplegable = document.getElementById("estado-local-horarios");

    if (!etiqueta || !detalle || !boton || !desplegable) {
        return;
    }

    const horarios = [
        { apertura: 630, cierre: 1020 },
        { apertura: 630, cierre: 1110 },
        { apertura: 630, cierre: 1110 },
        { apertura: 630, cierre: 1110 },
        { apertura: 630, cierre: 1110 },
        { apertura: 630, cierre: 1110 },
        { apertura: 630, cierre: 1110 }
    ];

    const dias = [
        "domingo",
        "lunes",
        "martes",
        "miércoles",
        "jueves",
        "viernes",
        "sábado"
    ];

    function obtenerHoraChile() {
        const formato = new Intl.DateTimeFormat("en-US", {
            timeZone: "America/Santiago",
            weekday: "short",
            hour: "2-digit",
            minute: "2-digit",
            hourCycle: "h23"
        });

        const partes = formato.formatToParts(new Date());
        const datos = {};

        partes.forEach(function (parte) {
            datos[parte.type] = parte.value;
        });

        const equivalencias = {
            Sun: 0,
            Mon: 1,
            Tue: 2,
            Wed: 3,
            Thu: 4,
            Fri: 5,
            Sat: 6
        };

        return {
            dia: equivalencias[datos.weekday],
            minutos: Number(datos.hour) * 60 + Number(datos.minute)
        };
    }

    function formatearHora(minutos) {
        const hora24 = Math.floor(minutos / 60);
        const minutosHora = minutos % 60;
        const periodo = hora24 < 12 ? "a. m." : "p. m.";
        const hora12 = hora24 % 12 || 12;

        return (
            hora12 +
            ":" +
            String(minutosHora).padStart(2, "0") +
            " " +
            periodo
        );
    }

    function actualizarEstado() {
        const ahora = obtenerHoraChile();
        const horario = horarios[ahora.dia];

        if (!horario) {
            etiqueta.textContent = "Horario no disponible";
            detalle.textContent = "";
            return;
        }

        const estaAbierto =
            ahora.minutos >= horario.apertura &&
            ahora.minutos < horario.cierre;

        etiqueta.classList.remove("abierto", "cerrado");

        if (estaAbierto) {
            etiqueta.textContent = "Abierto";
            etiqueta.classList.add("abierto");

            detalle.textContent =
                "· Cierra a las " + formatearHora(horario.cierre);
        } else {
            etiqueta.textContent = "Cerrado";
            etiqueta.classList.add("cerrado");

            if (ahora.minutos < horario.apertura) {
                detalle.textContent =
                    "· Abre hoy a las " +
                    formatearHora(horario.apertura);
            } else {
                const siguienteDia = (ahora.dia + 1) % 7;

                detalle.textContent =
                    "· Abre " +
                    dias[siguienteDia] +
                    " a las " +
                    formatearHora(horarios[siguienteDia].apertura);
            }
        }

        document.querySelectorAll(
            ".estado-local-fila"
        ).forEach(function (fila) {
            fila.classList.toggle(
                "dia-actual",
                Number(fila.dataset.dia) === ahora.dia
            );
        });
    }

    boton.addEventListener("click", function () {
        const expandido =
            boton.getAttribute("aria-expanded") === "true";

        boton.setAttribute(
            "aria-expanded",
            String(!expandido)
        );

        desplegable.hidden = expandido;
    });

    actualizarEstado();

    setInterval(actualizarEstado, 30000);

    document.addEventListener("visibilitychange", function () {
        if (!document.hidden) {
            actualizarEstado();
        }
    });
});
