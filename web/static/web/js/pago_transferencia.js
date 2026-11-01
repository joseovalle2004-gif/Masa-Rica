 document.querySelectorAll(
            "[data-copy-target]"
        ).forEach(function (boton) {

            boton.addEventListener("click", async function () {

                const identificador = boton.dataset.copyTarget;
                const elemento = document.getElementById(identificador);

                if (!elemento) {
                    return;
                }

                const texto = elemento.textContent.trim();

                try {
                    await navigator.clipboard.writeText(texto);

                    boton.textContent = "¡Copiado!";
                    boton.classList.add("copiado");

                    setTimeout(function () {
                        boton.textContent = "Copiar";
                        boton.classList.remove("copiado");
                    }, 2000);

                } catch (error) {
                    boton.textContent = "No se pudo copiar";

                    setTimeout(function () {
                        boton.textContent = "Copiar";
                    }, 2000);
                }

            });

        });