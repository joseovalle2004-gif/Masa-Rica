
document.addEventListener("DOMContentLoaded", function () {

    const formulario = document.getElementById("filtros-ventas");
    const fechaDesde = document.getElementById("fecha-desde");
    const fechaHasta = document.getElementById("fecha-hasta");

    const botonesPeriodo = document.querySelectorAll(
        "[data-periodo]"
    );

    function fechaLocal(fecha) {
        const anio = fecha.getFullYear();
        const mes = String(fecha.getMonth() + 1).padStart(2, "0");
        const dia = String(fecha.getDate()).padStart(2, "0");

        return `${anio}-${mes}-${dia}`;
    }

    botonesPeriodo.forEach(function (boton) {

        boton.addEventListener("click", function () {

            const periodo = boton.dataset.periodo;

            const hoy = new Date();
            const inicio = new Date(hoy);

            if (periodo === "7") {
                inicio.setDate(inicio.getDate() - 6);
            }

            if (periodo === "30") {
                inicio.setDate(inicio.getDate() - 29);
            }

            fechaDesde.value = fechaLocal(inicio);
            fechaHasta.value = fechaLocal(hoy);

            const buscar = document.getElementById("buscar");
            const metodo = document.getElementById("metodo");

            if (buscar) {
                buscar.value = "";
            }

            if (metodo) {
                metodo.value = "todos";
            }

            formulario.requestSubmit();

        });

    });

    const contenedor = document.getElementById("grafico-ventas");
    const elementoDatos = document.getElementById(
        "datos-grafico-ventas"
    );

    if (!contenedor || !elementoDatos) {
        return;
    }

    let datos = [];

    try {
        datos = JSON.parse(elementoDatos.textContent);
    } catch (error) {
        console.error("No se pudieron leer los datos del gráfico.");
        return;
    }

    if (!Array.isArray(datos) || datos.length === 0) {
        contenedor.textContent = "No hay datos para este período.";
        return;
    }

    const mayorIngreso = Math.max(
        0,
        ...datos.map(function (item) {
            return Number(item.total) || 0;
        })
    );

    if (mayorIngreso === 0) {
        const mensaje = document.createElement("p");

        mensaje.className = "grafico-vacio";
        mensaje.textContent =
            "No se registraron ingresos en los días seleccionados.";

        contenedor.appendChild(mensaje);
        return;
    }

    const formatoMoneda = new Intl.NumberFormat("es-CL", {
        style: "currency",
        currency: "CLP",
        maximumFractionDigits: 0
    });

    datos.forEach(function (item) {

        const total = Number(item.total) || 0;

        const columna = document.createElement("div");
        columna.className = "grafico-columna";

        const barra = document.createElement("div");
        barra.className = "grafico-barra";

        const porcentaje = (total / mayorIngreso) * 100;

        barra.style.height = `${Math.max(3, porcentaje * 1.7)}px`;

        barra.title = `${item.fecha}: ${formatoMoneda.format(total)}`;

        const fecha = document.createElement("span");
        fecha.className = "grafico-fecha";
        fecha.textContent = item.fecha;

        columna.appendChild(barra);
        columna.appendChild(fecha);

        contenedor.appendChild(columna);

    });

});
