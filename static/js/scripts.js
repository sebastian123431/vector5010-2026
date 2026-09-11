/**
 * VECTOR 2026 // Global UI Bridge & Sovereign Station Controller
 * Encargado de la gestión de la barra lateral, sincronización de sesiones estilo ChatGPT,
 * telemetría Centinela y eventos globales de interfaz.
 */

(function() {
    'use strict';

    // Manejo de Interfaz Móvil y Sidebar
    window.toggleSidebar = function() {
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) {
            sidebar.classList.toggle('open');
        }
    };

    // Sincronización de Identidad de Usuario en Sidebar
    window.syncUserIdentityUI = function() {
        const labelEl = document.getElementById('sidebar-user-name');
        if (labelEl) {
            const userName = localStorage.getItem('vector_user_name');
            labelEl.textContent = (userName && userName !== 'Invitado') ? userName : 'Vector 2026';
        }
    };

    // Cargar y renderizar sesiones en el sidebar estilo ChatGPT
    window.cargarSesionesSidebar = async function() {
        const sessionListContainer = document.getElementById('sidebar-session-list');
        if (!sessionListContainer) return;

        try {
            const currentSessionId = localStorage.getItem('vector_session_id') || '';
            const userName = localStorage.getItem('vector_user_name');
            const url = (userName && userName !== 'Invitado')
                ? `/api/chat/sesiones/?user_name=${encodeURIComponent(userName)}`
                : `/api/chat/sesiones/`;
            const res = await fetch(url);
            if (!res.ok) return;
            const data = await res.json();

            if (data.sesiones && data.sesiones.length > 0) {
                sessionListContainer.innerHTML = data.sesiones.slice(0, 20).map(s => {
                    const isActive = s.session_id === currentSessionId ? 'active' : '';
                    const titleSafe = escapeHtml(s.title || 'Conversación sin título');
                    return `
                        <div class="session-item ${isActive}" onclick="seleccionarSesionDesdeSidebar('${s.session_id}')" title="${titleSafe}">
                            <div class="session-info">
                                <div class="session-title">💬 ${titleSafe}</div>
                                <div class="session-meta">${s.created_at || ''} • ${s.message_count} msgs</div>
                            </div>
                        </div>
                    `;
                }).join('');
            } else {
                sessionListContainer.innerHTML = `
                    <div style="padding: 12px 8px; font-size: 11px; color: var(--text-dim); text-align: center;">
                        No hay sesiones previas registradas
                    </div>
                `;
            }
        } catch (err) {
            console.warn('No se pudieron cargar sesiones en el sidebar:', err);
        }
    };

    // Cambiar de sesión al hacer clic en el sidebar
    window.seleccionarSesionDesdeSidebar = function(sessionId) {
        if (!sessionId) return;
        localStorage.setItem('vector_session_id', sessionId);
        
        // Actualizar visualización activa
        document.querySelectorAll('.session-item').forEach(el => el.classList.remove('active'));
        
        // Si estamos en network.html y existe la función cargarTodoElHistorialEnChat
        if (typeof window.cargarTodoElHistorialEnChat === 'function') {
            window.cargarTodoElHistorialEnChat(50, sessionId);
        } else {
            window.location.href = '/redes/';
        }
        
        // Cerrar sidebar en pantallas táctiles
        const sidebar = document.querySelector('.sidebar');
        if (sidebar && sidebar.classList.contains('open')) {
            sidebar.classList.remove('open');
        }
    };

    // Monitoreo de Hardware Centinela en Sidebar
    window.actualizarTelemetriaCentinelaSidebar = async function() {
        try {
            const res = await fetch('/api/sentinel/status/');
            if (!res.ok) return;
            const data = await res.json();
            
            const cpuVal = document.getElementById('sidebar-cpu-val');
            const cpuFill = document.getElementById('sidebar-cpu-fill');
            const ramVal = document.getElementById('sidebar-ram-val');
            const ramFill = document.getElementById('sidebar-ram-fill');
            
            const rawCpu = data.cpu !== undefined ? data.cpu : data.cpu_percent;
            if (rawCpu !== undefined) {
                const cpu = Math.round(rawCpu);
                if (cpuVal) cpuVal.textContent = cpu + '%';
                if (cpuFill) cpuFill.style.width = Math.min(100, Math.max(0, cpu)) + '%';
            }
            const rawRam = data.ram !== undefined ? data.ram : data.ram_percent;
            if (rawRam !== undefined) {
                const ram = Math.round(rawRam);
                if (ramVal) ramVal.textContent = ram + '%';
                if (ramFill) ramFill.style.width = Math.min(100, Math.max(0, ram)) + '%';
            }
        } catch (e) {
            // Silencioso en fondo
        }
    };

    function escapeHtml(text) {
        if (!text) return '';
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Inicialización al cargar el DOM
    document.addEventListener('DOMContentLoaded', function() {
        syncUserIdentityUI();
        cargarSesionesSidebar();
        actualizarTelemetriaCentinelaSidebar();
        
        // Polling de telemetría cada 6 segundos
        setInterval(actualizarTelemetriaCentinelaSidebar, 6000);

        // Atajos de Teclado Globales
        document.addEventListener('keydown', function(e) {
            // Ctrl + N -> Nueva Conversación
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'n') {
                e.preventDefault();
                if (typeof window.iniciarNuevaConversacion === 'function') {
                    window.iniciarNuevaConversacion();
                }
            }
            // Ctrl + K -> Enfocar input de chat
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
                e.preventDefault();
                const chatInput = document.getElementById('chat-input');
                if (chatInput) chatInput.focus();
            }
            // Esc -> Cerrar inspector o HUD
            if (e.key === 'Escape') {
                if (typeof window.closeInspector === 'function') window.closeInspector();
                const visionHud = document.getElementById('vision-hud');
                if (visionHud && visionHud.style.display !== 'none') {
                    visionHud.style.display = 'none';
                }
            }
        });
    });

})();