
document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    // =========================================
    // ELEMENTOS DEL FORMULARIO
    // =========================================

    const formulario = document.getElementById("formulario-pedido");
    const nombre = document.getElementById("nombre_cliente");
    const telefono = document.getElementById("telefono_cliente");
    const observaciones = document.getElementById("observaciones");
    const totalElemento = document.getElementById("total-pedido");
    const botonGuardar = document.getElementById("boton-guardar-pedido");

    const cantidades = Array.from(
        document.querySelectorAll(".cantidad-producto")
    );

    if (
        !formulario ||
        !nombre ||
        !telefono ||
        !observaciones ||
        !totalElemento
    ) {
        console.error("Operia: faltan elementos del formulario.");
        return;
    }

    const MAX_CANTIDAD = 1000;

    // =========================================
    // FUNCIONES DE ERRORES
    // =========================================

    function mostrarError(campo, mensaje, idError = null) {
        campo.setCustomValidity(mensaje);
        campo.setAttribute("aria-invalid", "true");

        if (idError) {
            const elemento = document.getElementById(idError);

            if (elemento) {
                elemento.textContent = mensaje;
            }
        }
    }

    function limpiarError(campo, idError = null) {
        campo.setCustomValidity("");
        campo.removeAttribute("aria-invalid");

        if (idError) {
            const elemento = document.getElementById(idError);

            if (elemento) {
                elemento.textContent = "";
            }
        }
    }

    // =========================================
    // VALIDAR NOMBRE DEL CLIENTE
    // =========================================

    function validarNombre() {
        limpiarError(nombre, "error-nombre");

        const valor = nombre.value.trim().replace(/\s+/g, " ");

        if (valor.length < 2 || valor.length > 100) {
            mostrarError(
                nombre,
                "El nombre debe tener entre 2 y 100 caracteres.",
                "error-nombre"
            );
            return false;
        }

        const patron = /^[\p{L}]+(?:[ '-][\p{L}]+)*$/u;

        if (!patron.test(valor)) {
            mostrarError(
                nombre,
                "El nombre solo puede contener letras, espacios, guiones y apóstrofes.",
                "error-nombre"
            );
            return false;
        }

        return true;
    }

    // =========================================
    // VALIDAR TELÉFONO CHILENO
    // =========================================

    function validarTelefono() {
        limpiarError(telefono, "error-telefono");

        const valor = telefono.value.replace(/[\s()-]/g, "");

        // El teléfono es opcional.
        if (valor === "") {
            return true;
        }

        // Ejemplos:
        // 912345678
        // +56912345678
        // 221234567

        const patron = /^(?:\+56)?[2-9]\d{8}$/;

        if (!patron.test(valor)) {
            mostrarError(
                telefono,
                "Ingresa un teléfono chileno válido de 9 dígitos, con o sin +56.",
                "error-telefono"
            );
            return false;
        }

        return true;
    }

    // =========================================
    // VALIDAR OBSERVACIONES
    // =========================================

    function validarObservaciones() {
        limpiarError(observaciones, "error-observaciones");

        if (observaciones.value.length > 1000) {
            mostrarError(
                observaciones,
                "Las observaciones no pueden superar los 1000 caracteres.",
                "error-observaciones"
            );
            return false;
        }

        return true;
    }

    // =========================================
    // VALIDAR CANTIDADES
    // =========================================

    function validarCantidades() {
        let hayProductos = false;
        let todoValido = true;
        let primerCampoInvalido = null;

        const errorProductos = document.getElementById(
            "error-productos"
        );

        if (errorProductos) {
            errorProductos.textContent = "";
        }

        cantidades.forEach(function (campo) {
            limpiarError(campo);

            const texto = campo.value.trim();

            // Un campo vacío se interpreta como 0.
            const cantidad = texto === "" ? 0 : Number(texto);

            const formatoValido =
                texto === "" || /^\d+$/.test(texto);

            if (
                !formatoValido ||
                !Number.isSafeInteger(cantidad) ||
                cantidad < 0 ||
                cantidad > MAX_CANTIDAD
            ) {
                mostrarError(
                    campo,
                    "Ingresa un número entero entre 0 y 1000."
                );

                if (!primerCampoInvalido) {
                    primerCampoInvalido = campo;
                }

                todoValido = false;
                return;
            }

            // Normalizar campos vacíos para Django.
            if (texto === "") {
                campo.value = "0";
            }

            if (cantidad > 0) {
                hayProductos = true;
            }
        });

        if (!todoValido) {
            if (errorProductos) {
                errorProductos.textContent =
                    "Revisa las cantidades ingresadas.";
            }

            return false;
        }

        // Se exige al menos un producto con cantidad mayor a cero.
        if (!hayProductos) {
            if (errorProductos) {
                errorProductos.textContent =
                    "Debes seleccionar al menos un producto.";
            }

            return false;
        }

        return true;
    }

    // =========================================
    // CONVERTIR PRECIO A NÚMERO
    // =========================================

    function obtenerPrecio(valor) {
        let texto = String(valor ?? "").trim();

        texto = texto.replace(/[$\s]/g, "");

        // Formatos aceptados:
        // 2500
        // 2500.00
        // 2500,00
        // 2.500
        // 2.500,00

        if (/^\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?$/.test(texto)) {
            texto = texto.replace(/\./g, "").replace(",", ".");

        } else if (/^\d+(?:,\d{1,2})$/.test(texto)) {
            texto = texto.replace(",", ".");
        }

        const precio = Number(texto);

        if (!Number.isFinite(precio) || precio < 0) {
            return null;
        }

        return precio;
    }

    // =========================================
    // ACTUALIZAR TOTAL ESTIMADO
    // =========================================

    function actualizarTotal() {
        let total = 0;
        let preciosValidos = true;

        cantidades.forEach(function (campo) {
            const texto = campo.value.trim();
            const cantidad = texto === "" ? 0 : Number(texto);
            const precio = obtenerPrecio(campo.dataset.precio);

            if (precio === null) {
                preciosValidos = false;
                return;
            }

            if (
                (texto === "" || /^\d+$/.test(texto)) &&
                Number.isSafeInteger(cantidad) &&
                cantidad >= 0 &&
                cantidad <= MAX_CANTIDAD
            ) {
                total += cantidad * precio;
            }
        });

        if (!preciosValidos) {
            totalElemento.textContent = "Precio no disponible";
            totalElemento.dataset.total = "";
            return;
        }

        totalElemento.textContent = "$" + total.toLocaleString(
            "es-CL",
            {
                minimumFractionDigits: 0,
                maximumFractionDigits: 0
            }
        );

        totalElemento.dataset.total = String(total);
    }

    // =========================================
    // EVENTOS DE LOS CAMPOS
    // =========================================

    nombre.addEventListener("input", validarNombre);

    telefono.addEventListener("input", validarTelefono);

    observaciones.addEventListener(
        "input",
        validarObservaciones
    );

    cantidades.forEach(function (campo) {
        campo.addEventListener("input", function () {
            limpiarError(campo);

            const errorProductos = document.getElementById(
                "error-productos"
            );

            if (errorProductos) {
                errorProductos.textContent = "";
            }

            actualizarTotal();
        });

        campo.addEventListener("change", actualizarTotal);
    });

    // =========================================
    // VALIDAR Y GUARDAR PEDIDO
    // =========================================

    let enviando = false;

    formulario.addEventListener("submit", function (evento) {
        evento.preventDefault();

        if (enviando) {
            return;
        }

        const nombreValido = validarNombre();
        const telefonoValido = validarTelefono();
        const observacionesValidas = validarObservaciones();
        const cantidadesValidas = validarCantidades();

        const todoValido =
            nombreValido &&
            telefonoValido &&
            observacionesValidas &&
            cantidadesValidas;

        if (!todoValido) {
            const primerError = formulario.querySelector(
                '[aria-invalid="true"]'
            );

            if (primerError) {
                primerError.focus();
                primerError.reportValidity();

            } else {
                const errorProductos = document.getElementById(
                    "error-productos"
                );

                if (errorProductos) {
                    errorProductos.scrollIntoView({
                        behavior: "smooth",
                        block: "center"
                    });
                }
            }

            return;
        }

        actualizarTotal();

        if (totalElemento.dataset.total === "") {
            window.alert(
                "No se pudo calcular el total. Revisa los precios."
            );
            return;
        }

        enviando = true;

        if (botonGuardar) {
            botonGuardar.disabled = true;
            botonGuardar.textContent = "Guardando pedido...";
        }

        // Enviar el pedido a Django.
        HTMLFormElement.prototype.submit.call(formulario);
    });

    // =========================================
    // TOTAL INICIAL
    // =========================================

    actualizarTotal();
});
