
document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    const CLAVE_CARRITO = "masa_rica_carrito_v1";
    const MAX_CANTIDAD = 1000;
    const URL_CONFIRMAR = "/clientes/pedidos/confirmar/";

    const fondo = document.getElementById("carrito-fondo");
    const panel = document.getElementById("carrito-panel");
    const cerrar = document.getElementById("cerrar-carrito");
    const contenido = panel
        ? panel.querySelector(".carrito-contenido")
        : null;

    const botonesAbrir = document.querySelectorAll(".abrir-carrito");

    let elementoAnterior = null;
    let carrito = {};
    let procesandoPedido = false;
    let metodoPagoSeleccionado = "efectivo";
    let aceptaWhatsapp = null;
    let mensajeCarrito = "";
    let tipoMensaje = "";

    function formatoPrecio(numero) {
        return "$" + Number(numero).toLocaleString("es-CL", {
            maximumFractionDigits: 0
        });
    }

    function cantidadValida(valor) {
        const cantidad = Number(valor);

        return (
            Number.isSafeInteger(cantidad) &&
            cantidad >= 1 &&
            cantidad <= MAX_CANTIDAD
        );
    }

    function precioValido(valor) {
        return Number.isSafeInteger(valor) && valor >= 0;
    }

    function crearElemento(etiqueta, clase, texto) {
        const elemento = document.createElement(etiqueta);

        if (clase) {
            elemento.className = clase;
        }

        if (texto !== undefined) {
            elemento.textContent = texto;
        }

        return elemento;
    }

    function obtenerCookie(nombre) {
        const cookies = document.cookie
            ? document.cookie.split(";")
            : [];

        for (const cookie of cookies) {
            const valor = cookie.trim();

            if (valor.startsWith(nombre + "=")) {
                return decodeURIComponent(
                    valor.substring(nombre.length + 1)
                );
            }
        }

        return "";
    }

    function obtenerTokenCSRF() {
        const campo = document.querySelector(
            'input[name="csrfmiddlewaretoken"]'
        );

        if (campo && campo.value) {
            return campo.value;
        }

        return obtenerCookie("csrftoken");
    }

    function cargarCarrito() {
        try {
            const guardado = localStorage.getItem(CLAVE_CARRITO);

            if (!guardado) {
                return {};
            }

            const datos = JSON.parse(guardado);

            if (
                !datos ||
                typeof datos !== "object" ||
                Array.isArray(datos)
            ) {
                return {};
            }

            const resultado = {};

            Object.entries(datos).forEach(function ([id, producto]) {
                if (
                    !/^[1-9]\d*$/.test(id) ||
                    !Number.isSafeInteger(Number(id)) ||
                    !producto ||
                    typeof producto !== "object" ||
                    typeof producto.nombre !== "string" ||
                    !producto.nombre.trim() ||
                    producto.nombre.length > 120 ||
                    !precioValido(producto.precio) ||
                    !cantidadValida(producto.cantidad)
                ) {
                    return;
                }

                resultado[id] = {
                    id: id,
                    nombre: producto.nombre,
                    precio: producto.precio,
                    cantidad: producto.cantidad,
                    tipoVenta: producto.tipoVenta === "encargo"
                        ? "encargo"
                        : "diaria"
                };
            });

            return resultado;

        } catch (error) {
            console.error("Error al cargar el carrito:", error);
            return {};
        }
    }

    function guardarCarrito() {
        try {
            localStorage.setItem(
                CLAVE_CARRITO,
                JSON.stringify(carrito)
            );

            return true;

        } catch (error) {
            console.error("Error al guardar el carrito:", error);

            alert(
                "No se pudo guardar el carrito. " +
                "Revisa el almacenamiento del navegador."
            );

            return false;
        }
    }

    function actualizarContador() {
        const totalCantidad = Object.values(carrito).reduce(
            function (acumulado, producto) {
                return acumulado + producto.cantidad;
            },
            0
        );

        document.querySelectorAll(".contador-carrito").forEach(
            function (contador) {
                contador.textContent = totalCantidad;
                contador.hidden = totalCantidad === 0;
            }
        );
    }

    function abrirCarrito() {
        if (!fondo || !panel || !contenido) {
            console.error("No se encontró el panel del carrito.");
            return;
        }

        elementoAnterior = document.activeElement;

        renderizarCarrito();

        fondo.hidden = false;
        panel.hidden = false;

        document.body.classList.add("carrito-abierto");

        panel.setAttribute("tabindex", "-1");
        panel.focus();
    }

    function cerrarCarrito() {
        if (!fondo || !panel || procesandoPedido) {
            return;
        }

        fondo.hidden = true;
        panel.hidden = true;

        document.body.classList.remove("carrito-abierto");

        if (
            elementoAnterior &&
            elementoAnterior.isConnected &&
            typeof elementoAnterior.focus === "function"
        ) {
            elementoAnterior.focus();
        }
    }

    function agregarProducto(boton) {
        if (procesandoPedido) {
            return;
        }

        const id = boton.dataset.productoId;
        const nombre = boton.dataset.productoNombre;
        const precio = Number(boton.dataset.productoPrecio);
        const tipoVenta = boton.dataset.productoTipo;
        const idCantidad = boton.dataset.cantidadId;
        const campoCantidad = document.getElementById(idCantidad);

        if (!campoCantidad) {
            alert("No se encontró el selector de cantidad.");
            return;
        }

        const cantidad = Number(campoCantidad.value);

        if (!cantidadValida(cantidad)) {
            alert(
                "La cantidad debe ser un número entero entre 1 y 1000."
            );

            campoCantidad.focus();
            return;
        }

        if (
            !/^[1-9]\d*$/.test(id || "") ||
            !Number.isSafeInteger(Number(id)) ||
            !nombre ||
            !nombre.trim() ||
            !precioValido(precio)
        ) {
            alert("No se pudo identificar correctamente el producto.");
            return;
        }

        const cantidadActual = carrito[id]
            ? carrito[id].cantidad
            : 0;

        const cantidadNueva = cantidadActual + cantidad;

        if (cantidadNueva > MAX_CANTIDAD) {
            alert(
                "El máximo permitido es de 1000 unidades por producto."
            );
            return;
        }

        const carritoAnterior = { ...carrito };

        carrito[id] = {
            id: id,
            nombre: nombre,
            precio: precio,
            cantidad: cantidadNueva,
            tipoVenta: tipoVenta === "encargo"
                ? "encargo"
                : "diaria"
        };

        if (!guardarCarrito()) {
            carrito = carritoAnterior;
            return;
        }

        mensajeCarrito = "";
        tipoMensaje = "";

        actualizarContador();
        renderizarCarrito();
        abrirCarrito();
    }

    function cambiarCantidad(id, diferencia) {
        if (procesandoPedido || !carrito[id]) {
            return;
        }

        const nuevaCantidad = carrito[id].cantidad + diferencia;

        if (nuevaCantidad > MAX_CANTIDAD) {
            return;
        }

        const carritoAnterior = {
            ...carrito,
            [id]: { ...carrito[id] }
        };

        if (nuevaCantidad <= 0) {
            delete carrito[id];
        } else {
            carrito[id].cantidad = nuevaCantidad;
        }

        if (!guardarCarrito()) {
            carrito = carritoAnterior;
            return;
        }

        mensajeCarrito = "";
        tipoMensaje = "";

        actualizarContador();
        renderizarCarrito();
    }

    function eliminarProducto(id) {
        if (procesandoPedido || !carrito[id]) {
            return;
        }

        const productoAnterior = carrito[id];

        delete carrito[id];

        if (!guardarCarrito()) {
            carrito[id] = productoAnterior;
            return;
        }

        mensajeCarrito = "";
        tipoMensaje = "";

        actualizarContador();
        renderizarCarrito();
    }

    function mostrarMensaje(contenedor) {
        if (!mensajeCarrito) {
            return;
        }

        const mensaje = crearElemento(
            "p",
            "carrito-aviso",
            mensajeCarrito
        );

        mensaje.setAttribute("role", "status");

        if (tipoMensaje === "error") {
            mensaje.style.color = "#a32020";
        } else if (tipoMensaje === "exito") {
            mensaje.style.color = "#176534";
        }

        contenedor.appendChild(mensaje);
    }

    function mostrarCarritoVacio() {
        const vacio = crearElemento("div", "carrito-vacio");

        const icono = crearElemento(
            "span",
            "carrito-vacio-icono",
            "🛍️"
        );

        const titulo = crearElemento(
            "h3",
            "",
            "Tu carrito está vacío"
        );

        const descripcion = crearElemento(
            "p",
            "",
            "Explora nuestras preparaciones y encuentra tus favoritas."
        );

        const enlace = crearElemento(
            "a",
            "carrito-ver-productos",
            "Ver productos"
        );

        enlace.href = "/#productos";
        enlace.addEventListener("click", cerrarCarrito);

        vacio.append(icono, titulo, descripcion);

        mostrarMensaje(vacio);

        vacio.appendChild(enlace);
        contenido.appendChild(vacio);
    }

    function crearArticulo(producto) {
        const articulo = crearElemento(
            "article",
            "carrito-articulo"
        );

        const superior = crearElemento(
            "div",
            "carrito-articulo-superior"
        );

        const icono = crearElemento(
            "div",
            "carrito-articulo-icono",
            "🥟"
        );

        icono.setAttribute("aria-hidden", "true");

        const informacion = crearElemento(
            "div",
            "carrito-articulo-informacion"
        );

        const nombre = crearElemento(
            "h3",
            "",
            producto.nombre
        );

        const precio = crearElemento(
            "p",
            "",
            formatoPrecio(producto.precio) + " por unidad"
        );

        const subtotal = crearElemento(
            "strong",
            "",
            formatoPrecio(producto.precio * producto.cantidad)
        );

        informacion.append(nombre, precio, subtotal);
        superior.append(icono, informacion);

        const controles = crearElemento(
            "div",
            "carrito-controles"
        );

        const disminuir = crearElemento("button", "", "−");
        disminuir.type = "button";
        disminuir.disabled = procesandoPedido;

        disminuir.setAttribute(
            "aria-label",
            "Disminuir cantidad de " + producto.nombre
        );

        disminuir.addEventListener("click", function () {
            cambiarCantidad(producto.id, -1);
        });

        const cantidad = crearElemento(
            "span",
            "carrito-cantidad",
            String(producto.cantidad)
        );

        const aumentar = crearElemento("button", "", "+");
        aumentar.type = "button";

        aumentar.disabled = (
            procesandoPedido ||
            producto.cantidad >= MAX_CANTIDAD
        );

        aumentar.setAttribute(
            "aria-label",
            "Aumentar cantidad de " + producto.nombre
        );

        aumentar.addEventListener("click", function () {
            cambiarCantidad(producto.id, 1);
        });

        const eliminar = crearElemento(
            "button",
            "carrito-eliminar",
            "Eliminar"
        );

        eliminar.type = "button";
        eliminar.disabled = procesandoPedido;

        eliminar.addEventListener("click", function () {
            eliminarProducto(producto.id);
        });

        controles.append(
            disminuir,
            cantidad,
            aumentar,
            eliminar
        );

        articulo.append(superior, controles);

        return articulo;
    }

    function crearOpcionesPago() {
        const seccion = crearElemento(
            "div",
            "carrito-metodos-pago"
        );

        const titulo = crearElemento(
            "h3",
            "",
            "¿Cómo deseas pagar?"
        );

        const contenedorOpciones = crearElemento(
            "div",
            "carrito-opciones-pago"
        );

        const opciones = [
            {
                valor: "efectivo",
                titulo: "Efectivo",
                icono: "💵",
                descripcion: "Paga al retirar en el local.",
                disponible: true
            },
            {
                valor: "debito",
                titulo: "Tarjeta de débito",
                icono: "💳",
                descripcion:
                    "Pago con Webpay Plus de Transbank " +
                    "(ambiente de pruebas).",
                disponible: true
            },
            {
                valor: "credito",
                titulo: "Tarjeta de crédito",
                icono: "💳",
                descripcion:
                    "Pago con Webpay Plus de Transbank " +
                    "(ambiente de pruebas).",
                disponible: true
            },
            {
                valor: "transferencia",
                titulo: "Transferencia bancaria",
                icono: "🏦",
                descripcion:
                    "Datos bancarios después de confirmar. " +
                    "Pago pendiente de verificación.",
                disponible: true
            }
        ];

        opciones.forEach(function (opcion) {
            const etiqueta = crearElemento(
                "label",
                "carrito-opcion-pago"
            );

            const radio = document.createElement("input");
            radio.type = "radio";
            radio.name = "metodo_pago_carrito";
            radio.value = opcion.valor;

            radio.checked = (
                metodoPagoSeleccionado === opcion.valor &&
                opcion.disponible
            );

            radio.disabled = (
                procesandoPedido ||
                !opcion.disponible
            );

            etiqueta.classList.toggle(
                "seleccionada",
                radio.checked
            );

            etiqueta.classList.toggle(
                "no-disponible",
                !opcion.disponible
            );

            radio.addEventListener("change", function () {
                if (
                    radio.checked &&
                    opcion.disponible &&
                    !procesandoPedido
                ) {
                    metodoPagoSeleccionado = opcion.valor;
                    renderizarCarrito();
                }
            });

            const icono = crearElemento(
                "span",
                "carrito-opcion-pago-icono",
                opcion.icono
            );

            icono.setAttribute("aria-hidden", "true");

            const informacion = crearElemento("div", "");

            const nombre = crearElemento(
                "strong",
                "",
                opcion.titulo
            );

            const descripcion = crearElemento(
                "p",
                "",
                opcion.descripcion
            );

            informacion.append(nombre, descripcion);

            etiqueta.append(radio, icono, informacion);
            contenedorOpciones.appendChild(etiqueta);
        });

        seccion.append(titulo, contenedorOpciones);

        return seccion;
    }

    function crearOpcionesWhatsapp() {
        const seccion = crearElemento(
            "div",
            "carrito-autorizacion-whatsapp"
        );

        const titulo = crearElemento(
            "h3",
            "",
            "¿Quieres recibir un aviso por WhatsApp?"
        );

        const descripcion = crearElemento(
            "p",
            "",
            "Elige si autorizas recibir un mensaje cuando " +
            "tu pedido esté listo para retirar."
        );

        const contenedorOpciones = crearElemento(
            "div",
            "carrito-opciones-whatsapp"
        );

        const opciones = [
            {
                valor: "si",
                texto: "Sí, autorizo"
            },
            {
                valor: "no",
                texto: "No, gracias"
            }
        ];

        opciones.forEach(function (opcion) {
            const etiqueta = crearElemento(
                "label",
                "carrito-opcion-whatsapp"
            );

            const radio = document.createElement("input");
            radio.type = "radio";
            radio.name = "autorizacion_whatsapp";
            radio.value = opcion.valor;

            radio.checked = (
                aceptaWhatsapp === (opcion.valor === "si")
            );

            radio.disabled = procesandoPedido;

            etiqueta.classList.toggle(
                "seleccionada",
                radio.checked
            );

            radio.addEventListener("change", function () {
                if (radio.checked && !procesandoPedido) {
                    aceptaWhatsapp = opcion.valor === "si";
                    renderizarCarrito();
                }
            });

            const texto = crearElemento(
                "span",
                "",
                opcion.texto
            );

            etiqueta.append(radio, texto);
            contenedorOpciones.appendChild(etiqueta);
        });

        seccion.append(
            titulo,
            descripcion,
            contenedorOpciones
        );

        return seccion;
    }

    function enviarPedidoAWebpay(numeroPedido, tokenCSRF) {
        const formulario = document.createElement("form");

        formulario.method = "POST";
        formulario.action = (
            "/clientes/pedidos/" +
            encodeURIComponent(numeroPedido) +
            "/webpay/iniciar/"
        );

        const campoCSRF = document.createElement("input");
        campoCSRF.type = "hidden";
        campoCSRF.name = "csrfmiddlewaretoken";
        campoCSRF.value = tokenCSRF;

        formulario.appendChild(campoCSRF);
        document.body.appendChild(formulario);
        formulario.submit();
    }

    async function confirmarPedido() {
        if (procesandoPedido) {
            return;
        }

        const productos = Object.values(carrito);

        if (productos.length === 0) {
            mensajeCarrito = "Tu carrito está vacío.";
            tipoMensaje = "error";
            renderizarCarrito();
            return;
        }

        const metodosValidos = [
            "efectivo",
            "debito",
            "credito",
            "transferencia"
        ];

        if (!metodosValidos.includes(metodoPagoSeleccionado)) {
            mensajeCarrito = "Selecciona un método de pago válido.";
            tipoMensaje = "error";
            renderizarCarrito();
            return;
        }

        if (typeof aceptaWhatsapp !== "boolean") {
            mensajeCarrito = (
                "Debes indicar si autorizas o no recibir " +
                "avisos por WhatsApp antes de confirmar tu pedido."
            );

            tipoMensaje = "error";
            renderizarCarrito();
            return;
        }

        const tokenCSRF = obtenerTokenCSRF();

        if (!tokenCSRF) {
            mensajeCarrito = (
                "No se pudo verificar la seguridad de la sesión. " +
                "Recarga la página e inténtalo nuevamente."
            );

            tipoMensaje = "error";
            renderizarCarrito();
            return;
        }

        const productosEnviar = productos.map(function (producto) {
            return {
                id: Number(producto.id),
                cantidad: producto.cantidad
            };
        });

        const datosPedido = {
            productos: productosEnviar,
            metodo_pago: metodoPagoSeleccionado,
            acepta_whatsapp: aceptaWhatsapp
        };

        procesandoPedido = true;

        mensajeCarrito = (
            "Estamos registrando tu pedido. Por favor, espera..."
        );

        tipoMensaje = "";
        renderizarCarrito();

        try {
            const respuesta = await fetch(URL_CONFIRMAR, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": tokenCSRF,
                    "Accept": "application/json"
                },
                body: JSON.stringify(datosPedido)
            });

            let resultado = null;

            try {
                resultado = await respuesta.json();
            } catch (error) {
                resultado = null;
            }

            if (
                !respuesta.ok ||
                !resultado ||
                !resultado.ok
            ) {
                if (respuesta.status === 401) {
                    throw new Error(
                        "Debes iniciar sesión como cliente " +
                        "para confirmar tu pedido."
                    );
                }

                if (respuesta.status === 403) {
                    throw new Error(
                        "No se pudo autorizar la solicitud. " +
                        "Comprueba tu sesión y recarga la página."
                    );
                }

                throw new Error(
                    resultado && resultado.mensaje
                        ? resultado.mensaje
                        : "No se pudo confirmar el pedido."
                );
            }

            const numeroPedido = resultado.pedido_id;
            const totalConfirmado = resultado.total;
            const metodoConfirmado = resultado.metodo_pago;

            carrito = {};

            let carritoGuardado = true;

            try {
                localStorage.setItem(
                    CLAVE_CARRITO,
                    JSON.stringify(carrito)
                );
            } catch (error) {
                carritoGuardado = false;

                console.error(
                    "No se pudo limpiar el almacenamiento:",
                    error
                );
            }

            actualizarContador();

            if (
                metodoConfirmado === "debito" ||
                metodoConfirmado === "credito"
            ) {
                if (!carritoGuardado) {
                    mensajeCarrito = (
                        "El pedido #" + numeroPedido +
                        " fue registrado, pero no se pudo limpiar " +
                        "el carrito. Evita confirmarlo nuevamente " +
                        "y consulta Mis compras."
                    );

                    tipoMensaje = "error";
                    aceptaWhatsapp = null;
                    return;
                }

                mensajeCarrito = (
                    "Pedido #" + numeroPedido +
                    " registrado. Conectando con Webpay Plus..."
                );

                tipoMensaje = "";
                aceptaWhatsapp = null;

                enviarPedidoAWebpay(
                    numeroPedido,
                    tokenCSRF
                );

                return;
            }

            if (metodoConfirmado === "transferencia") {
                if (!carritoGuardado) {
                    mensajeCarrito = (
                        "El pedido #" + numeroPedido +
                        " fue registrado, pero no se pudo limpiar " +
                        "el carrito. Evita confirmarlo nuevamente " +
                        "y consulta Mis compras."
                    );

                    tipoMensaje = "error";
                    aceptaWhatsapp = null;
                    return;
                }

                aceptaWhatsapp = null;

                window.location.assign(
                    "/clientes/pedidos/" +
                    encodeURIComponent(numeroPedido) +
                    "/transferencia/"
                );

                return;
            }

            let mensajePago = "";

            if (metodoConfirmado === "efectivo") {
                mensajePago = (
                    "Podrás pagar en efectivo cuando retires tu pedido."
                );
            }

            mensajeCarrito = (
                "¡Pedido #" + numeroPedido +
                " registrado correctamente! " +
                "Total: " + formatoPrecio(totalConfirmado) +
                ". Presenta el número #" + numeroPedido +
                " al retirar tu pedido. " +
                mensajePago
            );

            if (!carritoGuardado) {
                mensajeCarrito += (
                    " Atención: no se pudo actualizar el almacenamiento " +
                    "del navegador. Evita volver a confirmar este pedido."
                );
            }

            tipoMensaje = "exito";
            aceptaWhatsapp = null;

        } catch (error) {
            console.error(
                "Error al confirmar el pedido:",
                error
            );

            mensajeCarrito = (
                error.message ||
                "No se pudo confirmar el pedido."
            );

            tipoMensaje = "error";

        } finally {
            procesandoPedido = false;
            actualizarContador();
            renderizarCarrito();
        }
    }

    function renderizarCarrito() {
        if (!contenido) {
            return;
        }

        contenido.replaceChildren();

        const productos = Object.values(carrito);

        if (productos.length === 0) {
            mostrarCarritoVacio();
            return;
        }

        const encabezadoProductos = crearElemento(
            "div",
            "carrito-seccion-titulo"
        );

        const tituloProductos = crearElemento(
            "span",
            "",
            "01 / PRODUCTOS"
        );

        const etiquetaRetiro = crearElemento(
            "span",
            "carrito-etiqueta-retiro",
            "⌖ Retiro en local"
        );

        encabezadoProductos.append(
            tituloProductos,
            etiquetaRetiro
        );

        const lista = crearElemento(
            "div",
            "carrito-lista"
        );

        let total = 0;

        productos.forEach(function (producto) {
            total += producto.precio * producto.cantidad;

            lista.appendChild(
                crearArticulo(producto)
            );
        });

        const resumen = crearElemento(
            "div",
            "carrito-resumen"
        );

        const filaTotal = crearElemento(
            "div",
            "carrito-total"
        );

        const etiqueta = crearElemento(
            "strong",
            "",
            "Total estimado"
        );

        const valorTotal = crearElemento(
            "strong",
            "",
            formatoPrecio(total)
        );

        filaTotal.append(etiqueta, valorTotal);

        const aviso = crearElemento(
            "p",
            "carrito-aviso",
            "El precio definitivo se calculará con los " +
            "valores vigentes en Masa Rica. El pedido " +
            "quedará pendiente de preparación."
        );

        const opcionesPago = crearOpcionesPago();
        const opcionesWhatsapp = crearOpcionesWhatsapp();

        const confirmar = crearElemento(
            "button",
            "carrito-confirmar",
            procesandoPedido
                ? "Registrando pedido..."
                : (
                    metodoPagoSeleccionado === "debito" ||
                    metodoPagoSeleccionado === "credito"
                )
                    ? "Confirmar y pagar con Webpay →"
                    : "Confirmar pedido →"
        );

        confirmar.type = "button";
        confirmar.disabled = procesandoPedido;

        confirmar.addEventListener(
            "click",
            confirmarPedido
        );

        const pie = crearElemento(
            "p",
            "carrito-pie",
            "Retiro en Masa Rica · Viña del Mar"
        );

        resumen.append(
            filaTotal,
            aviso,
            opcionesPago,
            opcionesWhatsapp
        );

        mostrarMensaje(resumen);

        resumen.append(confirmar, pie);

        contenido.append(
            encabezadoProductos,
            lista,
            resumen
        );
    }

    document.addEventListener("click", function (evento) {
        const boton = evento.target.closest(
            ".boton-agregar[data-producto-id]"
        );

        if (!boton) {
            return;
        }

        evento.preventDefault();
        agregarProducto(boton);
    });

    botonesAbrir.forEach(function (boton) {
        boton.addEventListener("click", abrirCarrito);
    });

    if (cerrar) {
        cerrar.addEventListener("click", cerrarCarrito);
    }

    if (fondo) {
        fondo.addEventListener("click", cerrarCarrito);
    }

    document.addEventListener("keydown", function (evento) {
        if (!panel || panel.hidden) {
            return;
        }

        if (evento.key === "Escape") {
            cerrarCarrito();
            return;
        }

        if (evento.key !== "Tab") {
            return;
        }

        const elementos = Array.from(
            panel.querySelectorAll(
                'a[href], button:not([disabled]), input:not([disabled])'
            )
        ).filter(function (elemento) {
            return elemento.getClientRects().length > 0;
        });

        if (!elementos.length) {
            evento.preventDefault();
            panel.focus();
            return;
        }

        const primero = elementos[0];
        const ultimo = elementos[elementos.length - 1];

        if (
            evento.shiftKey &&
            (
                document.activeElement === primero ||
                document.activeElement === panel
            )
        ) {
            evento.preventDefault();
            ultimo.focus();

        } else if (
            !evento.shiftKey &&
            document.activeElement === ultimo
        ) {
            evento.preventDefault();
            primero.focus();
        }
    });

    window.addEventListener("storage", function (evento) {
        if (
            evento.key === CLAVE_CARRITO &&
            !procesandoPedido
        ) {
            carrito = cargarCarrito();

            actualizarContador();
            renderizarCarrito();
        }
    });

    carrito = cargarCarrito();

    actualizarContador();
    renderizarCarrito();

    console.info(
        "Carrito de Masa Rica inicializado correctamente."
    );
});
