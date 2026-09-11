/**
 * Vector 2026 // Módulo Meteorológico
 * Archivo: weather-codes.js
 * Responsabilidad: Interpretación de códigos meteorológicos WMO (Open-Meteo)
 * y generación de iconografía vectorial SVG nativa sin dependencias externas.
 */

const WeatherCodes = (function () {
    'use strict';

    // Tabla de mapeo de códigos WMO según la especificación de Open-Meteo
    const wmoMap = {
        0: { text: "Despejado", icon: "sun" },
        1: { text: "Mayormente despejado", icon: "sun" },
        2: { text: "Parcialmente nublado", icon: "cloud-sun" },
        3: { text: "Nublado", icon: "cloud" },
        45: { text: "Niebla", icon: "cloud-fog" },
        48: { text: "Niebla con escarcha", icon: "cloud-fog" },
        51: { text: "Llovizna ligera", icon: "cloud-drizzle" },
        53: { text: "Llovizna moderada", icon: "cloud-drizzle" },
        55: { text: "Llovizna intensa", icon: "cloud-drizzle" },
        56: { text: "Llovizna helada ligera", icon: "cloud-drizzle" },
        57: { text: "Llovizna helada densa", icon: "cloud-drizzle" },
        61: { text: "Lluvia ligera", icon: "cloud-rain" },
        63: { text: "Lluvia moderada", icon: "cloud-rain" },
        65: { text: "Lluvia intensa", icon: "cloud-rain" },
        66: { text: "Lluvia helada ligera", icon: "cloud-rain" },
        67: { text: "Lluvia helada fuerte", icon: "cloud-rain" },
        71: { text: "Nieve ligera", icon: "snowflake" },
        73: { text: "Nieve moderada", icon: "snowflake" },
        75: { text: "Nieve intensa", icon: "snowflake" },
        77: { text: "Granos de nieve", icon: "snowflake" },
        80: { text: "Chubascos ligeros", icon: "cloud-rain" },
        81: { text: "Chubascos moderados", icon: "cloud-rain" },
        82: { text: "Chubascos fuertes", icon: "cloud-rain-wind" },
        85: { text: "Chubascos de nieve ligeros", icon: "snowflake" },
        86: { text: "Chubascos de nieve fuertes", icon: "snowflake" },
        95: { text: "Tormenta", icon: "cloud-lightning" },
        96: { text: "Tormenta con granizo", icon: "cloud-lightning" },
        99: { text: "Tormenta fuerte con granizo", icon: "cloud-lightning" }
    };

    /**
     * Obtiene la descripción textual y el identificador de icono para un código WMO.
     * @param {number|string} code - Código meteorológico WMO.
     * @returns {{ text: string, icon: string }}
     */
    function getInfo(code) {
        const numericCode = parseInt(code, 10);
        if (Object.prototype.hasOwnProperty.call(wmoMap, numericCode)) {
            return wmoMap[numericCode];
        }
        return { text: "Clima variable", icon: "cloud-sun" };
    }

    /**
     * Genera el marcado SVG de un icono meteorológico estilizado para Vector 2026.
     * @param {string} iconName - Nombre del icono ('sun', 'cloud-sun', 'cloud', etc.)
     * @param {number} [size=24] - Ancho y alto en píxeles.
     * @param {string} [extraClass=''] - Clases CSS adicionales.
     * @returns {string} Código HTML/SVG.
     */
    function renderIcon(iconName, size = 24, extraClass = '') {
        const s = size;
        const icon = (iconName || 'cloud-sun').toLowerCase();

        switch (icon) {
            case 'sun':
                return `<svg class="w-svg-icon icon-sun ${extraClass}" width="${s}" height="${s}" viewBox="0 0 24 24" aria-hidden="true">
                    <circle cx="12" cy="12" r="4"/>
                    <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>
                </svg>`;

            case 'cloud-sun':
                return `<svg class="w-svg-icon icon-sun ${extraClass}" width="${s}" height="${s}" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M12 2v2M4.93 4.93l1.41 1.41M20 12h2M19.07 4.93l-1.41 1.41M15.5 8a4 4 0 0 0-4.5 4"/>
                    <path d="M17.5 19H9a5 5 0 0 1-1-9.9 5 5 0 0 1 9.5 1.9 4 4 0 0 1 0 8z" stroke="currentColor"/>
                </svg>`;

            case 'cloud':
                return `<svg class="w-svg-icon icon-cloud ${extraClass}" width="${s}" height="${s}" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M17.5 19H9a5 5 0 0 1-1-9.9 5 5 0 0 1 9.5 1.9 4 4 0 0 1 0 8z"/>
                </svg>`;

            case 'cloud-fog':
                return `<svg class="w-svg-icon icon-cloud ${extraClass}" width="${s}" height="${s}" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"/>
                    <path d="M16 17H7M17 21H9"/>
                </svg>`;

            case 'cloud-drizzle':
                return `<svg class="w-svg-icon icon-rain ${extraClass}" width="${s}" height="${s}" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"/>
                    <path d="M8 19v1M8 14v1M12 21v1M12 16v1M16 19v1M16 14v1"/>
                </svg>`;

            case 'cloud-rain':
                return `<svg class="w-svg-icon icon-rain ${extraClass}" width="${s}" height="${s}" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"/>
                    <path d="M16 14v6M8 14v6M12 16v6"/>
                </svg>`;

            case 'cloud-rain-wind':
                return `<svg class="w-svg-icon icon-rain ${extraClass}" width="${s}" height="${s}" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"/>
                    <path d="m9.2 22 3-7M9 13l-3 7M17 13l-3 7"/>
                </svg>`;

            case 'snowflake':
                return `<svg class="w-svg-icon icon-snow ${extraClass}" width="${s}" height="${s}" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M2 12h20M12 2v20M20 16l-4-4 4-4M4 8l4 4-4 4M16 4l-4 4-4-4M8 20l4-4 4 4"/>
                </svg>`;

            case 'cloud-lightning':
                return `<svg class="w-svg-icon icon-lightning ${extraClass}" width="${s}" height="${s}" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M6 16.326A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 .5 8.973"/>
                    <path d="m13 12-3 5h4l-3 5"/>
                </svg>`;

            default:
                return `<svg class="w-svg-icon icon-sun ${extraClass}" width="${s}" height="${s}" viewBox="0 0 24 24" aria-hidden="true">
                    <circle cx="12" cy="12" r="4"/>
                    <path d="M12 2v2M12 20v2M2 12h2M20 12h2"/>
                </svg>`;
        }
    }

    return {
        codes: wmoMap,
        getInfo: getInfo,
        renderIcon: renderIcon
    };
})();

// Compatibilidad con entornos modulares o navegador global
if (typeof window !== 'undefined') {
    window.WeatherCodes = WeatherCodes;
}
