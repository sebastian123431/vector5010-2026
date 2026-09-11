/**
 * Vector 2026 // Módulo Meteorológico
 * Archivo: weather.js
 * Responsabilidad: Orquestador principal del clima, geolocalización multi-nivel de alta precisión
 * (GPS HTML5 + IP Geolocation + Backend Resolver + Búsqueda de Comunas/Ciudades con Open-Meteo Geocoding),
 * almacenamiento en caché localStorage (15 min) y despacho de actualizaciones dinámicas sin recarga.
 */

const WeatherManager = (function () {
    'use strict';

    // Parámetros de configuración y fallbacks inteligentes
    const DEFAULT_LAT = -30.0354;
    const DEFAULT_LON = -70.7127;
    const DEFAULT_LOCATION_LABEL = "📍 Vicuña, Región de Coquimbo, Chile";
    const CACHE_KEY = 'vector_weather_cache';
    const SAVED_LOC_KEY = 'vector_weather_saved_location';
    const CACHE_TTL_MS = 15 * 60 * 1000; // 15 minutos

    // Estado interno
    let currentLatitude = DEFAULT_LAT;
    let currentLongitude = DEFAULT_LON;
    let currentLocationLabel = DEFAULT_LOCATION_LABEL;
    let isFetching = false;
    let searchDebounceTimer = null;
    let domContainer = null;
    let locationLabelEl = null;

    /**
     * Obtiene la ubicación guardada preferida por el usuario si existe.
     */
    function getSavedLocation() {
        try {
            const raw = localStorage.getItem(SAVED_LOC_KEY);
            if (!raw) return null;
            const parsed = JSON.parse(raw);
            if (parsed && typeof parsed.lat === 'number' && typeof parsed.lon === 'number' && parsed.label) {
                return parsed;
            }
        } catch (e) {
            console.warn('[Vector Clima] Error leyendo ubicación guardada:', e);
        }
        return null;
    }

    /**
     * Guarda la ubicación preferida del usuario en localStorage.
     */
    function saveUserLocation(lat, lon, label) {
        try {
            localStorage.setItem(SAVED_LOC_KEY, JSON.stringify({ lat, lon, label }));
        } catch (e) {
            console.warn('[Vector Clima] No se pudo guardar ubicación preferida:', e);
        }
    }

    /**
     * Limpia la ubicación manual del usuario para forzar autodetección.
     */
    function clearUserLocation() {
        try {
            localStorage.removeItem(SAVED_LOC_KEY);
            localStorage.removeItem(CACHE_KEY);
        } catch (e) {
            console.warn('[Vector Clima] Error limpiando ubicación manual:', e);
        }
    }

    /**
     * Recupera los datos meteorológicos cacheados si aún no han expirado.
     * Si la caché contiene el texto antiguo hardcodeado "(Predeterminado)" o "Santiago",
     * la invalida inmediatamente para forzar la detección de la ubicación real del usuario.
     */
    function getCachedWeather() {
        try {
            const raw = localStorage.getItem(CACHE_KEY);
            if (!raw) return null;
            const parsed = JSON.parse(raw);
            const now = Date.now();

            if (parsed && parsed.timestamp && (now - parsed.timestamp < CACHE_TTL_MS) && parsed.data) {
                // Si la caché anterior quedó atrapada en el fallback genérico de Santiago, invalidarla
                if (parsed.label && (parsed.label.includes('Santiago, Chile (Predeterminado)') || parsed.label.includes('(Predeterminado)'))) {
                    localStorage.removeItem(CACHE_KEY);
                    return null;
                }
                return parsed;
            }
        } catch (e) {
            console.warn('[Vector Clima] No se pudo leer la caché local:', e);
        }
        return null;
    }

    /**
     * Persiste los datos meteorológicos en localStorage.
     */
    function saveCachedWeather(data, lat, lon, label) {
        try {
            const record = {
                data: data,
                timestamp: Date.now(),
                latitude: lat,
                longitude: lon,
                label: label
            };
            localStorage.setItem(CACHE_KEY, JSON.stringify(record));
        } catch (e) {
            console.warn('[Vector Clima] No se pudo guardar en caché:', e);
        }
    }

    /**
     * Nivel 1: GPS del Dispositivo (HTML5 Geolocation con alta precisión).
     */
    function tryGpsGeolocation(timeoutMs = 4500) {
        return new Promise((resolve, reject) => {
            if (typeof navigator === 'undefined' || !navigator.geolocation) {
                return reject(new Error('Geolocation no soportada por el navegador.'));
            }

            const timer = setTimeout(() => {
                reject(new Error('Tiempo de espera agotado en GPS.'));
            }, timeoutMs);

            navigator.geolocation.getCurrentPosition(
                async (position) => {
                    clearTimeout(timer);
                    const lat = position.coords.latitude;
                    const lon = position.coords.longitude;

                    // Geocodificación inversa para obtener el nombre exacto de la comuna
                    let locName = 'Ubicación GPS';
                    try {
                        const revRes = await fetch(`https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${lat}&longitude=${lon}&localityLanguage=es`);
                        if (revRes.ok) {
                            const revData = await revRes.json();
                            const comuna = revData.locality || revData.city || revData.principalSubdivision;
                            if (comuna) {
                                locName = `${comuna}, Chile (GPS)`;
                            }
                        }
                    } catch (_) {}

                    resolve({
                        lat: lat,
                        lon: lon,
                        label: `📍 ${locName}`
                    });
                },
                (err) => {
                    clearTimeout(timer);
                    reject(err);
                },
                {
                    enableHighAccuracy: true,
                    timeout: timeoutMs,
                    maximumAge: 60000
                }
            );
        });
    }

    /**
     * Nivel 2: Geocodificación IP de Alta Precisión (ipwho.is directo del navegador).
     */
    async function tryIpGeolocation(timeoutMs = 3500) {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), timeoutMs);
        try {
            const res = await fetch('https://ipwho.is/', { signal: controller.signal });
            clearTimeout(timer);
            if (!res.ok) return null;
            const data = await res.json();
            if (!data.success) return null;

            let city = data.city || '';
            if (city.toLowerCase() === 'vicuna') city = 'Vicuña';
            const region = data.region || '';
            const country = data.country || 'Chile';
            const label = region ? `📍 ${city}, ${region}, ${country} (Red/IP)` : `📍 ${city}, ${country} (Red/IP)`;

            return {
                lat: Number(data.latitude),
                lon: Number(data.longitude),
                label: label
            };
        } catch (e) {
            clearTimeout(timer);
            return null;
        }
    }

    /**
     * Nivel 3: Endpoint Servidor Django Local (/api/weather/locate/).
     */
    async function tryBackendGeolocation(timeoutMs = 3500) {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), timeoutMs);
        try {
            const res = await fetch('/api/weather/locate/', { signal: controller.signal });
            clearTimeout(timer);
            if (!res.ok) return null;
            const data = await res.json();
            if (data.latitude && data.longitude) {
                return {
                    lat: Number(data.latitude),
                    lon: Number(data.longitude),
                    label: data.label || `📍 ${data.city || 'Chile'}`
                };
            }
            return null;
        } catch (e) {
            clearTimeout(timer);
            return null;
        }
    }

    /**
     * Resuelve la ubicación más exacta posible utilizando el motor en cascada de Vector.
     * @returns {Promise<{ lat: number, lon: number, label: string }>}
     */
    async function resolveLocation() {
        // 1. Preferencia explícita guardada por el usuario
        const saved = getSavedLocation();
        if (saved && saved.lat && saved.lon) {
            console.log('[Vector Clima] Utilizando ubicación personalizada guardada:', saved.label);
            return saved;
        }

        // 2. Nivel 1: GPS del dispositivo
        try {
            const gpsLoc = await tryGpsGeolocation(3000);
            if (gpsLoc) {
                console.log('[Vector Clima] Ubicación exacta resuelta vía GPS:', gpsLoc.label);
                return gpsLoc;
            }
        } catch (e) {
            // Silencioso en fondo (típico en orígenes HTTP no seguros)
        }

        // 3. Nivel 2: Geocodificación IP directa en cliente
        try {
            const ipLoc = await tryIpGeolocation(3500);
            if (ipLoc) {
                console.log('[Vector Clima] Ubicación exacta resuelta vía IP cliente:', ipLoc.label);
                return ipLoc;
            }
        } catch (e) {
            // Silencioso en fondo
        }

        // 4. Nivel 3: Resolver del servidor Django
        try {
            const backendLoc = await tryBackendGeolocation(3500);
            if (backendLoc) {
                console.log('[Vector Clima] Ubicación resuelta vía servidor Django:', backendLoc.label);
                return backendLoc;
            }
        } catch (e) {
            // Silencioso en fondo
        }

        // 5. Nivel 4: Ubicación por defecto regional inteligente
        return {
            lat: DEFAULT_LAT,
            lon: DEFAULT_LON,
            label: DEFAULT_LOCATION_LABEL
        };
    }

    /**
     * Busca comunas o ciudades usando la API gratuita de geocodificación de Open-Meteo.
     * @param {string} query
     * @returns {Promise<Array>}
     */
    async function searchCities(query) {
        if (!query || query.trim().length < 2) return [];
        try {
            const url = `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(query.trim())}&count=8&language=es&format=json`;
            const res = await fetch(url);
            if (!res.ok) return [];
            const data = await res.json();
            if (!data.results) return [];

            // Priorizar resultados de Chile (CL)
            return data.results.sort((a, b) => {
                if (a.country_code === 'CL' && b.country_code !== 'CL') return -1;
                if (a.country_code !== 'CL' && b.country_code === 'CL') return 1;
                return 0;
            });
        } catch (e) {
            console.warn('[Vector Clima] Error en búsqueda de geocodificación:', e);
            return [];
        }
    }

    /**
     * Realiza la consulta a la API y actualiza la vista.
     * @param {boolean} forceRefresh - Si es true, ignora la caché y consulta directamente.
     */
    async function updateWeather(forceRefresh = false) {
        if (isFetching) {
            return;
        }

        if (!domContainer) {
            domContainer = document.getElementById('weather-content');
        }
        if (!locationLabelEl) {
            locationLabelEl = document.getElementById('weather-location-label');
        }

        if (!forceRefresh) {
            const cached = getCachedWeather();
            if (cached) {
                currentLatitude = cached.latitude;
                currentLongitude = cached.longitude;
                currentLocationLabel = cached.label || currentLocationLabel;

                if (locationLabelEl) {
                    locationLabelEl.textContent = currentLocationLabel;
                }
                WeatherUI.renderWeather(domContainer, cached.data, currentLocationLabel);
                return;
            }
        }

        // Mostrar estado de carga (skeleton loader)
        WeatherUI.showLoading(domContainer);
        WeatherUI.setRefreshingState(true);
        isFetching = true;

        try {
            // Resolver ubicación exacta
            const loc = await resolveLocation();
            currentLatitude = loc.lat;
            currentLongitude = loc.lon;
            currentLocationLabel = loc.label;

            if (locationLabelEl) {
                locationLabelEl.textContent = currentLocationLabel;
            }

            // Consultar Open-Meteo
            const weatherData = await WeatherAPI.fetchWeather(currentLatitude, currentLongitude);

            // Guardar en caché y renderizar
            saveCachedWeather(weatherData, currentLatitude, currentLongitude, currentLocationLabel);
            WeatherUI.renderWeather(domContainer, weatherData, currentLocationLabel);

        } catch (error) {
            console.error('[Vector Clima] Error al consultar Open-Meteo:', error);
            WeatherUI.showError(domContainer, error.message, () => {
                updateWeather(true);
            });
        } finally {
            isFetching = false;
            WeatherUI.setRefreshingState(false);
        }
    }

    /**
     * Función pública para refrescar los datos meteorológicos bajo demanda.
     */
    function refreshWeather() {
        updateWeather(true);
    }

    /**
     * Aplica una ubicación seleccionada manualmente por el usuario.
     */
    function applySelectedCity(lat, lon, label) {
        currentLatitude = Number(lat);
        currentLongitude = Number(lon);
        currentLocationLabel = label;
        saveUserLocation(currentLatitude, currentLongitude, currentLocationLabel);
        
        if (locationLabelEl) {
            locationLabelEl.textContent = currentLocationLabel;
        }

        // Ocultar panel de búsqueda
        const panel = document.getElementById('weather-search-panel');
        if (panel) panel.style.display = 'none';

        // Actualizar datos del clima de inmediato
        updateWeather(true);
    }

    /**
     * Configura los controladores de búsqueda interactiva de comunas / ciudades.
     */
    function setupLocationSearchUI() {
        const changeCityBtn = document.getElementById('weather-change-city-btn');
        const autoGpsBtn = document.getElementById('weather-auto-gps-btn');
        const searchPanel = document.getElementById('weather-search-panel');
        const cityInput = document.getElementById('weather-city-input');
        const searchBtn = document.getElementById('weather-city-search-btn');
        const closeBtn = document.getElementById('weather-city-close-btn');
        const resultsContainer = document.getElementById('weather-city-results');

        if (changeCityBtn && searchPanel) {
            changeCityBtn.addEventListener('click', (e) => {
                e.preventDefault();
                const isHidden = searchPanel.style.display === 'none' || !searchPanel.style.display;
                searchPanel.style.display = isHidden ? 'block' : 'none';
                if (isHidden && cityInput) {
                    cityInput.focus();
                }
            });
        }

        if (autoGpsBtn) {
            autoGpsBtn.addEventListener('click', (e) => {
                e.preventDefault();
                clearUserLocation();
                if (searchPanel) searchPanel.style.display = 'none';
                if (locationLabelEl) locationLabelEl.textContent = 'Detectando ubicación exacta...';
                refreshWeather();
            });
        }

        if (closeBtn && searchPanel) {
            closeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                searchPanel.style.display = 'none';
            });
        }

        async function triggerSearch() {
            if (!cityInput || !resultsContainer) return;
            const query = cityInput.value.trim();
            if (query.length < 2) {
                resultsContainer.style.display = 'none';
                resultsContainer.innerHTML = '';
                return;
            }

            resultsContainer.style.display = 'block';
            resultsContainer.innerHTML = '<div class="text-secondary small p-2 text-center"><span class="spinner-border spinner-border-sm text-info me-1"></span> Buscando comunas...</div>';

            const results = await searchCities(query);
            if (!results || results.length === 0) {
                resultsContainer.innerHTML = '<div class="text-secondary small p-2 text-center">No se encontraron ciudades o comunas coincidentes.</div>';
                return;
            }

            resultsContainer.innerHTML = '';
            results.forEach((item) => {
                const itemBtn = document.createElement('button');
                itemBtn.type = 'button';
                itemBtn.className = 'list-group-item list-group-item-action bg-dark text-light border-secondary d-flex justify-content-between align-items-center py-2 px-3';
                
                const regionName = item.admin1 ? `, ${item.admin1}` : '';
                const countryName = item.country ? `, ${item.country}` : '';
                const isChile = item.country_code === 'CL';
                const flagBadge = isChile ? '🇨🇱 ' : '';

                itemBtn.innerHTML = `
                    <span class="d-flex align-items-center gap-2">
                        <i class="bi bi-geo-alt-fill text-info"></i>
                        <span><strong>${flagBadge}${item.name}</strong><small class="text-secondary">${regionName}${countryName}</small></span>
                    </span>
                    <span class="badge ${isChile ? 'bg-success-subtle text-success-emphasis border border-success-subtle' : 'bg-secondary'} font-monospace small">
                        ${Number(item.latitude).toFixed(2)}°, ${Number(item.longitude).toFixed(2)}°
                    </span>
                `;

                itemBtn.addEventListener('click', () => {
                    const formattedLabel = `📍 ${item.name}${regionName}${countryName}`;
                    applySelectedCity(item.latitude, item.longitude, formattedLabel);
                });

                resultsContainer.appendChild(itemBtn);
            });
        }

        if (searchBtn) {
            searchBtn.addEventListener('click', (e) => {
                e.preventDefault();
                triggerSearch();
            });
        }

        if (cityInput) {
            cityInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    triggerSearch();
                }
            });

            cityInput.addEventListener('input', () => {
                clearTimeout(searchDebounceTimer);
                searchDebounceTimer = setTimeout(triggerSearch, 350);
            });
        }
    }

    /**
     * Alterna la visibilidad de la sección meteorológica en el DOM.
     * @param {boolean} [forceOpen=false]
     */
    function toggleWeatherSection(forceOpen = false) {
        const section = document.getElementById('weather-section');
        const btn = document.getElementById('btn-weather-toggle');
        if (!section) return;

        const isHidden = section.style.display === 'none';

        if (forceOpen || isHidden) {
            section.style.display = 'block';
            if (btn) btn.classList.add('active');
            section.scrollIntoView({ behavior: 'smooth', block: 'start' });
            if (!domContainer || domContainer.children.length === 0) {
                updateWeather(false);
            }
        } else {
            section.style.display = 'none';
            if (btn) btn.classList.remove('active');
        }
    }

    /**
     * Inicialización del módulo al cargar la página.
     */
    function init() {
        domContainer = document.getElementById('weather-content');
        locationLabelEl = document.getElementById('weather-location-label');

        const refreshBtn = document.getElementById('weather-refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', (e) => {
                e.preventDefault();
                refreshWeather();
            });
        }

        const collapseBtn = document.getElementById('weather-collapse-btn');
        if (collapseBtn) {
            collapseBtn.addEventListener('click', (e) => {
                e.preventDefault();
                toggleWeatherSection();
            });
        }

        // Configurar búsqueda interactiva y selección de comunas
        setupLocationSearchUI();

        // Cargar datos meteorológicos iniciales
        updateWeather(false);
    }

    return {
        init: init,
        refreshWeather: refreshWeather,
        toggleWeatherSection: toggleWeatherSection,
        updateWeather: updateWeather,
        searchCities: searchCities,
        applySelectedCity: applySelectedCity
    };
})();

// Auto-inicialización segura cuando el DOM esté listo
if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', WeatherManager.init);
    } else {
        WeatherManager.init();
    }
}

if (typeof window !== 'undefined') {
    window.WeatherManager = WeatherManager;
    window.refreshWeather = WeatherManager.refreshWeather;
    window.toggleWeatherSection = WeatherManager.toggleWeatherSection;
}
