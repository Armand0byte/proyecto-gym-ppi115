/* JavaScript de Rutinas: animaciones y búsqueda por grupo muscular. */
(function () {
    "use strict";

    // Se parte de una imagen fija. El GIF se carga solo cuando se reproduce.
    const reduceMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)");
    const botonesAnimacion = document.querySelectorAll("[data-animacion]");

    function cambiarAnimacion(boton, reproducir) {
        const imagen = document.getElementById(boton.getAttribute("aria-controls"));
        if (!imagen) return;
        const siguienteImagen = reproducir ? imagen.dataset.gif : imagen.dataset.estatica;
        if (imagen.getAttribute("src") !== siguienteImagen) {
            imagen.src = siguienteImagen;
        }
        boton.setAttribute("aria-pressed", String(reproducir));
        boton.textContent = reproducir ? "Detener animación" : "Reproducir animación";
    }

    botonesAnimacion.forEach(function (boton) {
        boton.hidden = false;
        cambiarAnimacion(boton, !reduceMovimiento.matches);
        boton.addEventListener("click", function () {
            cambiarAnimacion(boton, boton.getAttribute("aria-pressed") !== "true");
        });
    });

    // Respeta también un cambio de preferencia mientras la página está abierta.
    reduceMovimiento.addEventListener("change", function (evento) {
        if (evento.matches) {
            botonesAnimacion.forEach(function (boton) {
                cambiarAnimacion(boton, false);
            });
        }
    });

    const filtros = document.querySelector("[data-filtros]");
    if (!filtros) return;

    const buscador = document.getElementById("buscar-ejercicio");
    const tarjetas = Array.from(document.querySelectorAll("[data-ejercicio]"));
    const botonesFiltro = Array.from(document.querySelectorAll("[data-grupo-filtro]"));
    const resultado = document.getElementById("resultado-busqueda");
    const vacio = document.getElementById("busqueda-vacia");
    let grupoActual = "todos";
    filtros.hidden = false;

    function normalizar(texto) {
        return texto.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    }

    function filtrarEjercicios() {
        const texto = normalizar(buscador.value.trim());
        let cantidad = 0;
        tarjetas.forEach(function (tarjeta) {
            const coincideGrupo = grupoActual === "todos" || tarjeta.dataset.grupo === grupoActual;
            const coincideTexto = normalizar(tarjeta.dataset.ejercicio).includes(texto);
            tarjeta.hidden = !(coincideGrupo && coincideTexto);
            if (!tarjeta.hidden) cantidad++;
        });
        resultado.textContent = cantidad + (cantidad === 1 ? " ejercicio disponible" : " ejercicios disponibles");
        vacio.hidden = cantidad !== 0;
    }

    buscador.addEventListener("input", filtrarEjercicios);
    botonesFiltro.forEach(function (boton) {
        boton.addEventListener("click", function () {
            grupoActual = boton.dataset.grupoFiltro;
            botonesFiltro.forEach(function (otro) {
                otro.setAttribute("aria-pressed", String(otro === boton));
            });
            filtrarEjercicios();
        });
    });

    filtrarEjercicios();
})();
