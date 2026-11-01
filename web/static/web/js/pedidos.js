
"use strict";

// =============================================
// OPERIA - MASA RICA
// PROGRESO AUTOMÁTICO DE PEDIDOS
// =============================================

document.addEventListener("DOMContentLoaded", function () {

    const tarjetas = document.querySelectorAll(
        ".pedido-tarjeta[data-pedido-id]"
    );

    // =========================================
    // CALCULAR PORCENTAJE
    // =========================================

    function calcularPorcentaje(tarjeta) {

        const estado = tarjeta.dataset.estado;

        if (estado === "cancelado") {
            return 0;
        }

        if (estado === "entregado") {
            return 100;
        }

        if (estado === "listo") {
            return 80;
        }

        const fechaInicio = new Date(
            tarjeta.dataset.inicio
        ).getTime();

        const minutosEstimados = Number(
            tarjeta.dataset.minutos
        );

        if (
            !Number.isFinite(fechaInicio) ||
            !Number.isFinite(minutosEstimados) ||
            minutosEstimados <= 0
        ) {
            return null;
        }

        const tiempoTranscurrido = Math.max(
            0,
            Date.now() - fechaInicio
        );

        const duracionEstimada =
            minutosEstimados * 60 * 1000;

        const porcentaje = Math.floor(
            (tiempoTranscurrido / duracionEstimada) * 60
        );

        return Math.max(
            0,
            Math.min(porcentaje, 60)
        );
    }

    // =========================================
    // DETERMINAR ETAPA VISIBLE
    // =========================================

    function obtenerEtapa(estado, porcentaje) {

        if (estado === "cancelado") {
            return "Pedido cancelado";
        }

        if (estado === "entregado") {
            return "Retirado";
        }

        if (estado === "listo") {
            return "Listo para retirar";
        }

        if (porcentaje < 20) {
            return "Pedido recibido";
        }

        if (porcentaje < 40) {
            return "En preparación";
        }

        if (porcentaje < 60) {
            return "En cocción";
        }

        return "Esperando confirmación de cocina";
    }

    // =========================================
    // ACTUALIZAR ETAPAS VISUALES
    // =========================================

    function actualizarEtapas(tarjeta, porcentaje) {

        const etapas = tarjeta.querySelectorAll(
            ".progreso-etapa[data-etapa]"
        );

        etapas.forEach(function (etapa) {

            const numero = Number(
                etapa.dataset.etapa
            );

            const limite = numero * 20;

            etapa.classList.remove(
                "actual",
                "completada",
                "pendiente"
            );

            if (porcentaje >= limite) {

                etapa.classList.add("completada");

            } else if (
                numero === Math.min(
                    5,
                    Math.floor(porcentaje / 20) + 1
                )
            ) {

                etapa.classList.add("actual");

            } else {

                etapa.classList.add("pendiente");
            }

            const circulo = etapa.querySelector(
                ".etapa-circulo"
            );

            if (circulo) {

                circulo.textContent =
                    etapa.classList.contains("completada")
                        ? "✓"
                        : numero;
            }
        });
    }

    // =========================================
    // ACTUALIZAR UNA TARJETA
    // =========================================

    function actualizarPedido(tarjeta) {

        const estado = tarjeta.dataset.estado;

        const porcentaje = calcularPorcentaje(
            tarjeta
        );

        if (porcentaje === null) {
            return;
        }

        const textoPorcentaje = tarjeta.querySelector(
            ".progreso-porcentaje"
        );

        const barra = tarjeta.querySelector(
            ".progreso-relleno"
        );

        const pista = tarjeta.querySelector(
            ".progreso-pista"
        );

        const textoEstado = tarjeta.querySelector(
            ".pedido-estado-automatico"
        );

        if (textoPorcentaje) {
            textoPorcentaje.textContent =
                porcentaje + "%";
        }

        if (barra) {
            barra.style.width =
                porcentaje + "%";
        }

        if (pista) {
            pista.setAttribute(
                "aria-valuenow",
                String(porcentaje)
            );
        }

        if (textoEstado) {
            textoEstado.textContent = obtenerEtapa(
                estado,
                porcentaje
            );
        }

        actualizarEtapas(
            tarjeta,
            porcentaje
        );
    }

    // =========================================
    // ACTUALIZAR TODOS LOS PEDIDOS
    // =========================================

    function actualizarTodosLosPedidos() {

        tarjetas.forEach(function (tarjeta) {
            actualizarPedido(tarjeta);
        });
    }

    // Ejecutar al abrir la página.
    actualizarTodosLosPedidos();

    // Recalcular cada segundo.
    window.setInterval(
        actualizarTodosLosPedidos,
        1000
    );

    // =========================================
    // CONFIRMAR ENTREGA
    // =========================================

    const formulariosEntrega = document.querySelectorAll(
        ".formulario-entrega"
    );

    formulariosEntrega.forEach(function (formulario) {

        formulario.addEventListener(
            "submit",
            function (evento) {

                const confirmado = window.confirm(
                    "¿Confirmas que el cliente retiró su pedido?"
                );

                if (!confirmado) {
                    evento.preventDefault();
                }
            }
        );
    });

    // =========================================
    // EVITAR DOBLE ENVÍO
    // =========================================

    const formulariosAccion = document.querySelectorAll(
        ".formulario-accion"
    );

    formulariosAccion.forEach(function (formulario) {

        formulario.addEventListener(
            "submit",
            function (evento) {

                if (evento.defaultPrevented) {
                    return;
                }

                const boton = formulario.querySelector(
                    'button[type="submit"]'
                );

                if (boton) {
                    boton.disabled = true;
                }
            }
        );
    });

});
