/**
 * Vector 2026 // Módulo Meteorológico
 * Archivo: weather-ui.js
 * Responsabilidad: Exclusivamente manipulación y actualización del DOM,
 * generación de tarjetas, estados de carga (skeleton), formateo y alertas de error.
 */

const WeatherUI = (function () {
    'use strict';

    /**
     * Convierte los grados de orientación del viento en dirección cardinal en español.
     * @param {number} deg - Grados de 0 a 360.
     * @returns {string} Dirección cardinal ('N', 'NE', 'E', 'SE', 'S', 'SO', 'O', 'NO').
     */
    function windDegreesToCardinal(deg) {
        if (typeof deg !== 'number' || isNaN(deg)) return '--';
        const normalized = (deg % 360 + 360) % 360;
        const directions = ['N', 'NE', 'E', 'SE', 'S', 'SO', 'O', 'NO'];
        const index = Math.round(normalized / 45) % 8;
        return directions[index];
    }

    /**
     * Extrae solo la hora en formato HH:mm a partir de un string ISO.
     * @param {string} isoString - Fecha en formato 'YYYY-MM-DDTHH:mm'.
     * @returns {string} 'HH:mm'
     */
    function formatHourOnly(isoString) {
        if (!isoString) return '--:--';
        const parts = isoString.split('T');
        if (parts.length > 1) {
            return parts[1].substring(0, 5);
        }
        const d = new Date(isoString);
        return isNaN(d.getTime()) ? isoString : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
    }

    /**
     * Formatea el nombre del día de la semana en español con mayúscula inicial.
     * @param {string} dateString - 'YYYY-MM-DD'.
     * @param {boolean} isToday - Si corresponde a la fecha actual.
     * @returns {string} 'Hoy' o 'Lunes', 'Martes', etc.
     */
    function formatDayName(dateString, isToday = false) {
        if (isToday) return 'Hoy';
        if (!dateString) return 'Día';
        const parts = dateString.split('-');
        if (parts.length === 3) {
            // Se utiliza constructor con componentes locales para evitar desfasajes por zona horaria UTC
            const d = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
            const dayName = d.toLocaleDateString('es-ES', { weekday: 'long' });
            return dayName.charAt(0).toUpperCase() + dayName.slice(1);
        }
        return dateString;
    }

    /**
     * Muestra el skeleton loader dentro del contenedor del clima.
     * @param {HTMLElement} container - Elemento contenedor #weather-content.
     */
    function showLoading(container) {
        if (!container) return;
        container.innerHTML = `
            <div class="weather-skeleton" aria-live="polite" aria-busy="true">
                <div style="display:flex; align-items:center; gap:8px; color:var(--text-muted); font-size:12px; margin-bottom:4px;">
                    <div style="width:14px; height:14px; border:2px solid var(--cyan-neon); border-top-color:transparent; border-radius:50%; animation:spin 0.8s linear infinite;"></div>
                    <span>Obteniendo información meteorológica satelital...</span>
                </div>
                <div class="skeleton-box skeleton-hero"></div>
                <div class="skeleton-box skeleton-hourly"></div>
            </div>
        `;
    }

    /**
     * Muestra un mensaje de error discreto con botón para reintentar.
     * @param {HTMLElement} container - Elemento contenedor.
     * @param {string} message - Mensaje descriptivo.
     * @param {Function} retryCallback - Función a invocar al hacer clic en Reintentar.
     */
    function showError(container, message, retryCallback) {
        if (!container) return;
        container.innerHTML = `
            <div class="weather-error-box" role="alert">
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="font-size:18px;">⚠️</span>
                    <div>
                        <div style="font-weight:600; color:var(--text-pure);">No fue posible obtener la información meteorológica.</div>
                        <div style="font-size:11.5px; color:var(--text-muted); margin-top:2px;">${message || 'Inténtalo nuevamente más tarde.'}</div>
                    </div>
                </div>
                <button type="button" class="btn-retry" id="weather-btn-retry">Reintentar</button>
            </div>
        `;

        const retryBtn = container.querySelector('#weather-btn-retry');
        if (retryBtn && typeof retryCallback === 'function') {
            retryBtn.addEventListener('click', (e) => {
                e.preventDefault();
                retryCallback();
            });
        }
    }

    /**
     * Renderiza por completo la vista meteorológica en el DOM.
     * @param {HTMLElement} container - Contenedor principal de contenido.
     * @param {Object} data - Objeto de datos devuelto por Open-Meteo.
     * @param {string} locationLabel - Etiqueta textual de la ubicación detectada.
     */
    function renderWeather(container, data, locationLabel) {
        if (!container || !data || !data.current || !data.daily || !data.hourly) {
            showError(container, "Datos incompletos recibidos de Open-Meteo.", null);
            return;
        }

        const current = data.current;
        const daily = data.daily;
        const hourly = data.hourly;

        // 1. Interpretación de códigos meteorológicos
        const codeInfo = WeatherCodes.getInfo(current.weather_code);
        const heroSvg = WeatherCodes.renderIcon(codeInfo.icon, 72, 'weather-hero-svg');

        // 2. Extracción de valores meteorológicos actuales
        const temp = Math.round(current.temperature_2m);
        const apparentTemp = Math.round(current.apparent_temperature);
        const humidity = current.relative_humidity_2m ?? '--';
        const windSpeed = Math.round(current.wind_speed_10m ?? 0);
        const windDirCardinal = windDegreesToCardinal(current.wind_direction_10m);
        const windGusts = Math.round(current.wind_gusts_10m ?? windSpeed);
        const pressure = Math.round(current.pressure_msl ?? 1013);
        const cloudCover = current.cloud_cover ?? '--';
        const precipitation = current.precipitation ?? 0;

        // Horarios de Sol (Amanecer / Atardecer del día 0)
        const sunriseTime = (daily.sunrise && daily.sunrise[0]) ? formatHourOnly(daily.sunrise[0]) : '--:--';
        const sunsetTime = (daily.sunset && daily.sunset[0]) ? formatHourOnly(daily.sunset[0]) : '--:--';

        // 3. Renderizado del Pronóstico Horario (Próximas 12 - 24 Horas futuras)
        const now = new Date();
        const currentIsoHourPrefix = now.toISOString().slice(0, 13); // 'YYYY-MM-DDTHH'
        const hourlyCardsHtml = [];
        let countHours = 0;
        let foundCurrent = false;

        if (hourly.time && Array.isArray(hourly.time)) {
            for (let i = 0; i < hourly.time.length; i++) {
                const hourStr = hourly.time[i];
                const hourDate = new Date(hourStr);

                // Omitir horas ya ocurridas en el pasado (con margen de 50 minutos)
                if (hourDate.getTime() < now.getTime() - (50 * 60 * 1000)) {
                    continue;
                }

                const isNow = (!foundCurrent && hourStr.startsWith(currentIsoHourPrefix)) || countHours === 0;
                if (isNow) foundCurrent = true;

                const hTemp = Math.round(hourly.temperature_2m[i]);
                const hCode = hourly.weather_code[i];
                const hRainProb = hourly.precipitation_probability ? hourly.precipitation_probability[i] : 0;
                const hIconInfo = WeatherCodes.getInfo(hCode);
                const hIconSvg = WeatherCodes.renderIcon(hIconInfo.icon, 24);
                const timeDisplay = countHours === 0 ? 'Ahora' : formatHourOnly(hourStr);

                hourlyCardsHtml.push(`
                    <div class="weather-hourly-card ${countHours === 0 ? 'is-now' : ''}" title="${hIconInfo.text} - ${hTemp}°C">
                        <span class="weather-hourly-time">${timeDisplay}</span>
                        <div class="weather-hourly-icon">${hIconSvg}</div>
                        <span class="weather-hourly-temp">${hTemp}°</span>
                        <span class="weather-hourly-rain">💧 ${hRainProb}%</span>
                    </div>
                `);

                countHours++;
                if (countHours >= 20) break; // Límite de 20 slots horarios
            }
        }

        // 4. Renderizado del Pronóstico de los Próximos 7 Días
        const dailyRowsHtml = [];
        if (daily.time && Array.isArray(daily.time)) {
            for (let d = 0; d < Math.min(daily.time.length, 7); d++) {
                const dayDateStr = daily.time[d];
                const dayLabel = formatDayName(dayDateStr, d === 0);
                const dCode = daily.weather_code[d];
                const dIconInfo = WeatherCodes.getInfo(dCode);
                const dIconSvg = WeatherCodes.renderIcon(dIconInfo.icon, 20);
                const maxT = Math.round(daily.temperature_2m_max[d]);
                const minT = Math.round(daily.temperature_2m_min[d]);
                const rainProbMax = (daily.precipitation_probability_max && daily.precipitation_probability_max[d] !== undefined)
                    ? daily.precipitation_probability_max[d]
                    : 0;

                dailyRowsHtml.push(`
                    <div class="weather-daily-row" title="${dIconInfo.text}: máx ${maxT}° / mín ${minT}°">
                        <span class="weather-daily-day ${d === 0 ? 'is-today' : ''}">${dayLabel}</span>
                        <div class="weather-daily-icon">${dIconSvg}</div>
                        <div class="weather-daily-temps">
                            <span class="weather-temp-max">${maxT}°</span>
                            <span class="weather-temp-sep">/</span>
                            <span class="weather-temp-min">${minT}°</span>
                        </div>
                        <span class="weather-daily-rain">💧 ${rainProbMax}%</span>
                    </div>
                `);
            }
        }

        // 5. Ensamble de la Interfaz Completa
        container.innerHTML = `
            <div class="weather-grid">
                <!-- Columna 1: Tarjeta del Clima Actual y Métricas -->
                <div class="weather-current-card">
                    <div class="weather-hero-row">
                        <div class="weather-hero-temp-box">
                            <div class="weather-hero-temp">
                                ${temp}<span class="temp-unit">°C</span>
                            </div>
                            <div class="weather-hero-desc">${codeInfo.text}</div>
                            <div class="weather-hero-apparent">
                                Sensación térmica: <strong>${apparentTemp} °C</strong>
                            </div>
                        </div>
                        <div class="weather-hero-icon-container">
                            ${heroSvg}
                        </div>
                    </div>

                    <!-- Métricas de Precisión Atmosférica -->
                    <div class="weather-metrics-grid">
                        <div class="weather-metric-item">
                            <span class="weather-metric-label">💧 Humedad</span>
                            <span class="weather-metric-val highlight-cyan">${humidity}%</span>
                        </div>
                        <div class="weather-metric-item">
                            <span class="weather-metric-label">🌬️ Viento</span>
                            <span class="weather-metric-val">${windSpeed} km/h <span style="color:var(--cyan-neon); font-size:11px;">${windDirCardinal}</span></span>
                        </div>
                        <div class="weather-metric-item">
                            <span class="weather-metric-label">💨 Ráfagas</span>
                            <span class="weather-metric-val">${windGusts} km/h</span>
                        </div>
                        <div class="weather-metric-item">
                            <span class="weather-metric-label">⏲️ Presión</span>
                            <span class="weather-metric-val">${pressure} hPa</span>
                        </div>
                        <div class="weather-metric-item">
                            <span class="weather-metric-label">☁️ Nubes</span>
                            <span class="weather-metric-val">${cloudCover}%</span>
                        </div>
                        <div class="weather-metric-item">
                            <span class="weather-metric-label">🌧️ Lluvia</span>
                            <span class="weather-metric-val">${precipitation} mm</span>
                        </div>
                        <div class="weather-metric-item">
                            <span class="weather-metric-label">🌅 Amanecer</span>
                            <span class="weather-metric-val highlight-amber">${sunriseTime}</span>
                        </div>
                        <div class="weather-metric-item">
                            <span class="weather-metric-label">🌇 Atardecer</span>
                            <span class="weather-metric-val highlight-amber">${sunsetTime}</span>
                        </div>
                    </div>
                </div>

                <!-- Columna 2: Pronóstico de los Próximos 7 Días -->
                <div class="weather-daily-card">
                    <div class="weather-subheading">
                        <span>📅</span> Próximos 7 Días
                    </div>
                    <div class="weather-daily-list">
                        ${dailyRowsHtml.join('')}
                    </div>
                </div>
            </div>

            <!-- Fila Inferior: Pronóstico por Horas (Carrusel Horizontal) -->
            <div class="weather-hourly-section">
                <div class="weather-subheading" style="margin-bottom:8px;">
                    <span>⏱️</span> Pronóstico por Horas
                </div>
                <div class="weather-hourly-track">
                    ${hourlyCardsHtml.join('')}
                </div>
            </div>
        `;

        // Actualizar mini insignia en el header de la estación si existe
        updateHeaderMiniBadge(temp, codeInfo.text, codeInfo.icon);
    }

    /**
     * Actualiza la insignia compacta del encabezado del cockpit.
     */
    function updateHeaderMiniBadge(temp, description, iconName) {
        const badge = document.getElementById('weather-header-badge');
        const tempEl = document.getElementById('header-weather-temp');
        const descEl = document.getElementById('header-weather-desc');

        if (badge && tempEl) {
            badge.style.display = 'inline-flex';
            tempEl.textContent = `${temp}°C`;
            if (descEl) descEl.textContent = `(${description})`;
        }
    }

    /**
     * Alterna la clase CSS animada del botón de actualización.
     * @param {boolean} isRefreshing
     */
    function setRefreshingState(isRefreshing) {
        const btn = document.getElementById('weather-refresh-btn');
        if (btn) {
            if (isRefreshing) {
                btn.classList.add('refreshing');
            } else {
                btn.classList.remove('refreshing');
            }
        }
    }

    return {
        showLoading: showLoading,
        showError: showError,
        renderWeather: renderWeather,
        updateHeaderMiniBadge: updateHeaderMiniBadge,
        setRefreshingState: setRefreshingState,
        windDegreesToCardinal: windDegreesToCardinal
    };
})();

if (typeof window !== 'undefined') {
    window.WeatherUI = WeatherUI;
}
