
document.addEventListener("DOMContentLoaded", () => {

    const canvas = document.getElementById("grafico-ingresos");
    const fuente = document.getElementById("datos-ingresos-reportes");
    const vacio = document.getElementById("grafico-vacio");

    if (!canvas || !fuente || !vacio) {
        return;
    }

    let datos;

    try {
        datos = JSON.parse(fuente.textContent);
    } catch (error) {
        vacio.hidden = false;
        canvas.hidden = true;
        return;
    }

    if (!Array.isArray(datos) || datos.length === 0) {
        vacio.hidden = false;
        canvas.hidden = true;
        return;
    }

    const valores = datos.map(item => {
        const numero = Number(item.total);
        return Number.isFinite(numero) ? numero : 0;
    });

    const maximo = Math.max(0, ...valores);

    if (maximo <= 0) {
        vacio.hidden = false;
        canvas.hidden = true;
        return;
    }

    const contexto = canvas.getContext("2d");

    if (!contexto) {
        return;
    }

    const formatoPesos = new Intl.NumberFormat("es-CL", {
        style: "currency",
        currency: "CLP",
        maximumFractionDigits: 0
    });

    let indiceActivo = -1;
    let barras = [];

    function dibujar() {

        const rectangulo = canvas.getBoundingClientRect();
        const ancho = rectangulo.width;
        const alto = rectangulo.height;

        if (ancho <= 0 || alto <= 0) {
            return;
        }

        const escala = window.devicePixelRatio || 1;

        canvas.width = Math.round(ancho * escala);
        canvas.height = Math.round(alto * escala);

        contexto.setTransform(
            escala,
            0,
            0,
            escala,
            0,
            0
        );

        contexto.clearRect(0, 0, ancho, alto);

        const margen = {
            izquierda: ancho < 500 ? 54 : 78,
            derecha: 17,
            arriba: 42,
            abajo: 45
        };

        const anchoGrafico = ancho - margen.izquierda - margen.derecha;
        const altoGrafico = alto - margen.arriba - margen.abajo;

        if (anchoGrafico <= 0 || altoGrafico <= 0) {
            return;
        }

        const escalaMaxima = maximo * 1.15;

        contexto.font = "11px Segoe UI, Arial";
        contexto.textAlign = "right";
        contexto.textBaseline = "middle";

        for (let paso = 0; paso <= 4; paso++) {

            const valor = escalaMaxima * paso / 4;

            const y = margen.arriba
                + altoGrafico * (1 - paso / 4);

            contexto.strokeStyle = "#eee8e2";
            contexto.lineWidth = 1;

            contexto.beginPath();
            contexto.moveTo(margen.izquierda, y);
            contexto.lineTo(ancho - margen.derecha, y);
            contexto.stroke();

            contexto.fillStyle = "#8b8079";

            let etiqueta;

            if (valor >= 1000000) {
                etiqueta = (valor / 1000000).toFixed(1) + "M";
            } else if (valor >= 1000) {
                etiqueta = Math.round(valor / 1000) + "k";
            } else {
                etiqueta = Math.round(valor).toString();
            }

            contexto.fillText(
                "$" + etiqueta,
                margen.izquierda - 12,
                y
            );
        }

        const espacio = anchoGrafico / datos.length;
        const anchoBarra = Math.min(36, espacio * 0.56);

        barras = [];

        datos.forEach((item, indice) => {

            const valor = valores[indice];
            const alturaBarra = valor / escalaMaxima * altoGrafico;

            const x = margen.izquierda
                + espacio * indice
                + (espacio - anchoBarra) / 2;

            const y = margen.arriba
                + altoGrafico
                - alturaBarra;

            barras.push({
                x: x,
                y: y,
                ancho: anchoBarra,
                alto: alturaBarra,
                valor: valor
            });

            const gradiente = contexto.createLinearGradient(
                0,
                y,
                0,
                margen.arriba + altoGrafico
            );

            if (indice === indiceActivo) {
                gradiente.addColorStop(0, "#c77c61");
                gradiente.addColorStop(1, "#92362e");
            } else {
                gradiente.addColorStop(0, "#ac5146");
                gradiente.addColorStop(1, "#641f20");
            }

            contexto.fillStyle = gradiente;

            if (valor > 0) {
                contexto.beginPath();
                contexto.roundRect(
                    x,
                    y,
                    anchoBarra,
                    Math.max(alturaBarra, 2),
                    [5, 5, 0, 0]
                );
                contexto.fill();
            }

            contexto.fillStyle = "#81756e";
            contexto.textAlign = "center";
            contexto.textBaseline = "middle";
            contexto.font = "10px Segoe UI, Arial";

            if (datos.length <= 7 || indice % 2 === 0) {
                contexto.fillText(
                    item.fecha,
                    x + anchoBarra / 2,
                    alto - 18
                );
            }
        });

        if (indiceActivo >= 0 && barras[indiceActivo]) {

            const barra = barras[indiceActivo];
            const texto = formatoPesos.format(barra.valor);

            contexto.font = "bold 12px Segoe UI, Arial";

            const anchoTexto = contexto.measureText(texto).width;
            const anchoTooltip = anchoTexto + 28;

            const centro = Math.max(
                margen.izquierda + anchoTooltip / 2,
                Math.min(
                    ancho - margen.derecha - anchoTooltip / 2,
                    barra.x + barra.ancho / 2
                )
            );

            const posicionY = Math.max(5, barra.y - 40);

            contexto.fillStyle = "#392521";
            contexto.beginPath();
            contexto.roundRect(
                centro - anchoTooltip / 2,
                posicionY,
                anchoTooltip,
                31,
                7
            );
            contexto.fill();

            contexto.fillStyle = "#ffffff";
            contexto.textAlign = "center";
            contexto.textBaseline = "middle";

            contexto.fillText(
                texto,
                centro,
                posicionY + 15
            );
        }
    }

    canvas.addEventListener("mousemove", evento => {

        const rectangulo = canvas.getBoundingClientRect();
        const x = evento.clientX - rectangulo.left;

        let nuevoIndice = -1;

        barras.forEach((barra, indice) => {

            if (
                x >= barra.x - 6 &&
                x <= barra.x + barra.ancho + 6
            ) {
                nuevoIndice = indice;
            }
        });

        if (nuevoIndice !== indiceActivo) {
            indiceActivo = nuevoIndice;

            canvas.style.cursor = nuevoIndice >= 0
                ? "pointer"
                : "default";

            dibujar();
        }
    });

    canvas.addEventListener("mouseleave", () => {
        indiceActivo = -1;
        dibujar();
    });

    window.addEventListener("resize", dibujar);

    dibujar();
});
