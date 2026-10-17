/* Medición opcional: no carga Google hasta disponer de un ID real y consentimiento. */
(function () {
    "use strict";
    const config = window.RAYNOVIK_CONFIG || {};
    const id = String(config.analyticsId || "");
    const origenScript = document.currentScript ? document.currentScript.src : new URL("js/medicion.js", config.siteUrl).href;
    const privacidadURL = new URL("../privacidad.html", origenScript).href;
    const disponible = /^G-[A-Z0-9]+$/.test(id);
    const clave = "raynovik-medicion-v1";
    let decision = null;
    let cargada = false;
    let activa = false;
    let aviso;
    let origenFoco;
    try { decision = localStorage.getItem(clave); } catch (_) { /* La navegación funciona sin almacenamiento. */ }

    function estado() {
        document.querySelectorAll("[data-estado-medicion]").forEach(function (elemento) {
            elemento.textContent = !disponible ? "La medición de visitas está sin activar en este sitio." :
                decision === "aceptar" ? "Has aceptado la medición de visitas. Puedes cambiar tu preferencia cuando quieras." :
                decision === "rechazar" ? "Has rechazado la medición de visitas. Puedes seguir usando todas las guías." :
                "Puedes elegir si permites la medición de visitas.";
        });
    }

    if (!disponible) { estado(); return; }

    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };
    window.gtag("consent", "default", {
        analytics_storage: "denied", ad_storage: "denied",
        ad_user_data: "denied", ad_personalization: "denied"
    });

    function activar() {
        window["ga-disable-" + id] = false;
        window.gtag("consent", "update", { analytics_storage: "granted" });
        if (!cargada) {
            window.gtag("js", new Date());
            window.gtag("config", id, { allow_google_signals: false, allow_ad_personalization_signals: false });
            const script = document.createElement("script");
            script.async = true;
            script.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(id);
            document.head.appendChild(script);
            cargada = true;
        }
        activa = true;
    }

    function borrarCookiesDeMedicion() {
        const nombres = document.cookie.split(";").map(function (cookie) { return cookie.split("=")[0].trim(); })
            .filter(function (nombre) { return /^_ga(?:_|$)/.test(nombre); });
        const rutas = new Set(["/", new URL(config.siteUrl).pathname]);
        location.pathname.split("/").slice(0, -1).reduce(function (ruta, parte) {
            const siguiente = ruta + parte + "/";
            rutas.add(siguiente); return siguiente;
        }, "");
        nombres.forEach(function (nombre) {
            rutas.forEach(function (ruta) {
                ["", "; domain=" + location.hostname, "; domain=." + location.hostname].forEach(function (dominio) {
                    document.cookie = nombre + "=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=" + ruta + dominio + "; SameSite=Lax";
                });
            });
        });
    }

    function elegir(valor) {
        decision = valor;
        try { localStorage.setItem(clave, valor); } catch (_) { /* Preferencia válida durante esta visita. */ }
        if (valor === "aceptar") activar();
        else {
            activa = false;
            window["ga-disable-" + id] = true;
            window.gtag("consent", "update", { analytics_storage: "denied" });
            borrarCookiesDeMedicion();
        }
        aviso.hidden = true;
        estado();
        if (origenFoco && document.contains(origenFoco)) origenFoco.focus();
    }

    aviso = document.createElement("section");
    aviso.className = "aviso-medicion";
    aviso.setAttribute("role", "region");
    aviso.setAttribute("aria-labelledby", "titulo-medicion");
    aviso.innerHTML = '<h2 id="titulo-medicion">Medición de visitas</h2>' +
        '<p>Podemos usar Google Analytics para conocer qué guías resultan más útiles. Tú eliges si permites esta medición. <a href="privacidad.html">Ver privacidad</a>.</p>' +
        '<div class="aviso-medicion-acciones"><button type="button" data-elegir="aceptar">Aceptar medición</button>' +
        '<button type="button" data-elegir="rechazar">Rechazar medición</button></div>';
    aviso.hidden = decision === "aceptar" || decision === "rechazar";
    aviso.querySelector("a").href = privacidadURL;
    document.body.appendChild(aviso);
    aviso.querySelectorAll("[data-elegir]").forEach(function (boton) {
        boton.addEventListener("click", function () { elegir(boton.dataset.elegir); });
    });
    document.querySelectorAll("[data-preferencias-medicion]").forEach(function (boton) {
        boton.hidden = false;
        boton.addEventListener("click", function () {
            origenFoco = boton;
            aviso.hidden = false;
            aviso.querySelector("button").focus();
        });
    });
    document.addEventListener("click", function (evento) {
        if (!activa) return;
        const enlace = evento.target.closest("a");
        if (!enlace) return;
        if (enlace.hasAttribute("data-descarga-guia")) {
            window.gtag("event", "descargar_guia", { recurso: "guia_inicio_raynovik" });
        } else if (enlace.closest(".social-links, .contacto-grid")) {
            const url = new URL(enlace.href);
            const plataforma = url.hostname.replace(/^www\./, "");
            if (["instagram.com", "facebook.com", "tiktok.com"].includes(plataforma)) {
                window.gtag("event", "visitar_red_social", { plataforma: plataforma });
            }
        }
    });
    if (decision === "aceptar") activar();
    estado();
})();
