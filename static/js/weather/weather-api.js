/**
 * Vector 2026 // Módulo Meteorológico
 * Archivo: weather-api.js
 * Responsabilidad: Construcción de URLs, ejecución de peticiones HTTP con fetch(),
 * control de timeouts y gestión de errores de conexión con Open-Meteo.
 */

const WeatherAPI = (function () {
    'use strict';

    const BASE_URL = 'https://api.open-meteo.com/v1/forecast';
    const DEFAULT_TIMEOUT_MS = 12000;

    /**
     * Construye dinámicamente la URL para Open-Meteo con todos los parámetros requeridos.
     * @param {number} latitude - Latitud geográfica.
     * @param {number} longitude - Longitud geográfica.
     * @returns {string} URL formateada.
     */
    function buildUrl(latitude, longitude) {
        if (typeof latitude !== 'number' || typeof longitude !== 'number' || isNaN(latitude) || isNaN(longitude)) {
            throw new Error(`Coordenadas inválidas: lat=${latitude}, lon=${longitude}`);
        }

        const params = new URLSearchParams({
            latitude: latitude.toFixed(4),
            longitude: longitude.toFixed(4),
            current: 'temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,cloud_cover,pressure_msl,wind_speed_10m,wind_direction_10m,wind_gusts_10m',
            hourly: 'temperature_2m,apparent_temperature,precipitation_probability,weather_code,relative_humidity_2m,wind_speed_10m',
            daily: 'weather_code,temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,precipitation_probability_max,sunrise,sunset',
            timezone: 'auto',
            forecast_days: '7'
        });

        return `${BASE_URL}?${params.toString()}`;
    }

    /**
     * Realiza la consulta asíncrona a la API de Open-Meteo.
     * @param {number} latitude - Latitud.
     * @param {number} longitude - Longitud.
     * @param {number} [timeoutMs=12000] - Tiempo máximo de espera en milisegundos.
     * @returns {Promise<Object>} Datos meteorológicos devueltos por Open-Meteo.
     */
    async function fetchWeather(latitude, longitude, timeoutMs = DEFAULT_TIMEOUT_MS) {
        // Validación de conectividad del navegador
        if (typeof navigator !== 'undefined' && navigator.onLine === false) {
            throw new Error("No hay conexión a Internet. Verifica tu conectividad de red.");
        }

        const url = buildUrl(latitude, longitude);
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

        try {
            const response = await fetch(url, {
                method: 'GET',
                signal: controller.signal,
                headers: {
                    'Accept': 'application/json'
                }
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                let errorDetails = `Código de estado: ${response.status} ${response.statusText}`;
                try {
                    const errJson = await response.json();
                    if (errJson && errJson.reason) {
                        errorDetails += ` (${errJson.reason})`;
                    }
                } catch (_) {
                    // Si no es JSON, continuar con el texto estándar
                }
                throw new Error(`Error en servicio meteorológico Open-Meteo: ${errorDetails}`);
            }

            const data = await response.json();

            // Validación de integridad mínima del payload esperado
            if (!data || !data.current || !data.daily || !data.hourly) {
                throw new Error("Respuesta incompleta de Open-Meteo: faltan bloques esenciales.");
            }

            return data;
        } catch (error) {
            clearTimeout(timeoutId);

            if (error.name === 'AbortError') {
                throw new Error(`Tiempo de espera agotado (${timeoutMs / 1000}s) al contactar Open-Meteo.`);
            }
            throw error;
        }
    }

    return {
        buildUrl: buildUrl,
        fetchWeather: fetchWeather
    };
})();

if (typeof window !== 'undefined') {
    window.WeatherAPI = WeatherAPI;
}
