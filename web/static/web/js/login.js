
document.addEventListener("DOMContentLoaded", function () {

    const boton = document.getElementById("mostrar-password");
    const password = document.getElementById("password");

    if (!boton || !password) {
        return;
    }

    boton.addEventListener("click", function () {

        const mostrar = password.type === "password";

        password.type = mostrar ? "text" : "password";

        boton.textContent = mostrar ? "Ocultar" : "Mostrar";

        boton.setAttribute(
            "aria-label",
            mostrar ? "Ocultar contraseña" : "Mostrar contraseña"
        );

        boton.setAttribute("aria-pressed", String(mostrar));

    });

});
