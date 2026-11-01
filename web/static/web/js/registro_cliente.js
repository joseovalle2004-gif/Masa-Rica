
/* =====================================================
   MASA RICA - REGISTRO DE CLIENTES
   Validaciones del formulario
===================================================== */

document.addEventListener("DOMContentLoaded", function () {

    // =============================================
    // ELEMENTOS DEL FORMULARIO
    // =============================================

    const formulario = document.getElementById(
        "formulario-registro"
    );

    const nombre = document.getElementById(
        "nombre_completo"
    );

    const telefono = document.getElementById(
        "telefono"
    );

    const password1 = document.getElementById(
        "password1"
    );

    const password2 = document.getElementById(
        "password2"
    );

    const errorPassword = document.getElementById(
        "error-password"
    );

    const botonRegistro = document.getElementById(
        "boton-registro"
    );

    if (
        !formulario ||
        !nombre ||
        !telefono ||
        !password1 ||
        !password2 ||
        !errorPassword ||
        !botonRegistro
    ) {
        return;
    }

    // =============================================
    // EXPRESIONES REGULARES
    // =============================================

    // Letras Unicode, espacios, apóstrofes y guiones.
    // Debe comenzar y terminar con una letra.
    const patronNombre =
        /^\p{L}+(?:[ '-]\p{L}+)*$/u;

    // Teléfono chileno de 9 dígitos,
    // opcionalmente precedido por +56.
    const patronTelefono =
        /^(?:\+56)?[2-9]\d{8}$/;

    // =============================================
    // NORMALIZAR NOMBRE
    // =============================================

    function normalizarNombre() {

        nombre.value = nombre.value
            .trim()
            .replace(/\s+/g, " ");

    }

    // =============================================
    // NORMALIZAR TELÉFONO
    // =============================================

    function normalizarTelefono() {

        telefono.value = telefono.value.trim();

    }

    function limpiarTelefono() {

        return telefono.value.replace(
            /[\s()-]/g,
            ""
        );

    }

    // =============================================
    // VALIDAR NOMBRE
    // =============================================

    function validarNombre() {

        normalizarNombre();

        const valor = nombre.value;

        if (valor.split(" ").length < 2) {

            nombre.setCustomValidity(
                "Ingresa tu nombre y apellido."
            );

            return false;
        }

        if (!patronNombre.test(valor)) {

            nombre.setCustomValidity(
                "El nombre solo puede contener letras, " +
                "espacios, guiones o apóstrofes."
            );

            return false;
        }

        nombre.setCustomValidity("");

        return true;
    }

    // =============================================
    // VALIDAR TELÉFONO
    // =============================================

    function validarTelefono() {

        normalizarTelefono();

        const telefonoLimpio = limpiarTelefono();

        if (!patronTelefono.test(telefonoLimpio)) {

            telefono.setCustomValidity(
                "Ingresa un teléfono chileno válido " +
                "de 9 dígitos, con o sin +56."
            );

            return false;
        }

        telefono.setCustomValidity("");

        return true;
    }

    // =============================================
    // VALIDAR CONTRASEÑA PRINCIPAL
    // =============================================

    function validarPasswordPrincipal() {

        if (password1.value.length < 8) {

            password1.setCustomValidity(
                "La contraseña debe tener " +
                "al menos 8 caracteres."
            );

            return false;
        }

        password1.setCustomValidity("");

        return true;
    }

    // =============================================
    // VALIDAR CONFIRMACIÓN DE CONTRASEÑA
    // =============================================

    function validarContrasenas() {

        if (password2.value === "") {

            errorPassword.textContent = "";

            password2.setCustomValidity("");

            return true;
        }

        if (password1.value !== password2.value) {

            const mensaje =
                "Las contraseñas no coinciden.";

            errorPassword.textContent = mensaje;

            password2.setCustomValidity(mensaje);

            return false;
        }

        errorPassword.textContent = "";

        password2.setCustomValidity("");

        return true;
    }

    // =============================================
    // VALIDACIÓN DEL NOMBRE
    // =============================================

    nombre.addEventListener("input", function () {

        nombre.setCustomValidity("");

    });

    nombre.addEventListener("blur", function () {

        if (nombre.value.trim() !== "") {
            validarNombre();
        }

    });

    // =============================================
    // VALIDACIÓN DEL TELÉFONO
    // =============================================

    telefono.addEventListener("input", function () {

        telefono.setCustomValidity("");

    });

    telefono.addEventListener("blur", function () {

        if (telefono.value.trim() !== "") {
            validarTelefono();
        }

    });

    // =============================================
    // VALIDACIÓN DE CONTRASEÑAS EN TIEMPO REAL
    // =============================================

    password1.addEventListener("input", function () {

        password1.setCustomValidity("");

        validarContrasenas();

    });

    password2.addEventListener("input", function () {

        validarContrasenas();

    });

    // =============================================
    // VALIDAR ANTES DE ENVIAR
    // =============================================

    formulario.addEventListener("submit", function (evento) {

        // Evitar envíos duplicados.
        if (formulario.dataset.enviando === "true") {

            evento.preventDefault();

            return;
        }

        // Validar nombre.
        if (!validarNombre()) {

            evento.preventDefault();

            nombre.reportValidity();

            return;
        }

        // Validar teléfono.
        if (!validarTelefono()) {

            evento.preventDefault();

            telefono.reportValidity();

            return;
        }

        // Validar longitud de contraseña.
        if (!validarPasswordPrincipal()) {

            evento.preventDefault();

            password1.reportValidity();

            return;
        }

        // Validar coincidencia de contraseñas.
        if (!validarContrasenas()) {

            evento.preventDefault();

            password2.reportValidity();

            return;
        }

        // Confirmar que todos los campos sean válidos.
        if (!formulario.checkValidity()) {

            evento.preventDefault();

            formulario.reportValidity();

            return;
        }

        // =========================================
        // FORMULARIO VÁLIDO
        // =========================================

        formulario.dataset.enviando = "true";

        botonRegistro.disabled = true;

        botonRegistro.textContent = "Creando cuenta...";

    });

    // =============================================
    // RECUPERAR BOTÓN SI SE RESTAURA LA PÁGINA
    // =============================================

    window.addEventListener("pageshow", function () {

        formulario.dataset.enviando = "false";

        botonRegistro.disabled = false;

        botonRegistro.textContent = "Crear mi cuenta";

    });

});
