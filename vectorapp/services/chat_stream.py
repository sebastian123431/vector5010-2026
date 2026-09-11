import json
import requests
import logging
import re
from datetime import datetime
from typing import Generator
from django.conf import settings
from ..local_engine import VectorLocalEngine
from ..models import Interaction
from ..neural_network import semantic_network

logger = logging.getLogger(__name__)

SYSTEM_TAG_PREFIXES = (
    '[PERCEPCI', '[MEMORIA', '[RECUERD', '[SISTEMA',
    '[CONTEXTO', '[INFORMACI', '[RESULTAD'
)

def stream_chat_completion(messages: list, raw_user_message: str = "", user=None, skip_cache: bool = False, user_name: str = "", session_id: str = "") -> Generator[str, None, None]:
    """
    Generador que transmite tokens en tiempo real (Server-Sent Events) desde el motor local llama-server.
    Filtra en vuelo cualquier residuo de etiquetas de sistema preservando enlaces markdown y sintaxis de código.
    Registra interacciones asociadas a la sesión activa (session_id) sin contaminar la memoria a largo plazo con charlas efímeras.
    """
    VectorLocalEngine.ensure_engines()

    import time
    t_start = time.perf_counter()
    from ..query_optimizer import query_optimizer

    # Comprobar si existe respuesta directa instantánea o en caché (omitido si hay archivo adjunto)
    if not skip_cache:
        cached_reply = query_optimizer.get_cached_response(raw_user_message, user_name=user_name)
        if not cached_reply:
            cached_reply = query_optimizer.get_simple_response(raw_user_message, user_name=user_name)

        if cached_reply:
            try:
                Interaction.objects.create(
                    user=user,
                    question=raw_user_message,
                    answer=cached_reply,
                    session_id=session_id or "",
                    user_name=user_name or ""
                )
            except Exception as se:
                logger.warning(f"[ChatStream] Aviso al persistir interacción rápida: {se}")
            yield f"data: {json.dumps({'token': cached_reply}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True, 'full_response': cached_reply, 'user_name': user_name, 'session_id': session_id}, ensure_ascii=False)}\n\n"
            return

    url = f"http://127.0.0.1:{settings.LOCAL_CHAT_PORT}/v1/chat/completions"
    payload = {
        "messages": messages,
        "temperature": 0.35,
        "max_tokens": 1024,
        "repeat_penalty": 1.18,
        "presence_penalty": 0.2,
        "stream": True,
    }

    full_response = []
    bracket_buffer = ""
    in_bracket = False
    strip_next_space = False
    prefix_buffer = ""
    prefix_cleared = False
    
    try:
        session = VectorLocalEngine.get_session()
        with session.post(url, json=payload, stream=True, timeout=90) as resp:
            resp.raise_for_status()
            resp.encoding = 'utf-8'
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        token = delta.get("content", "")
                        if not token:
                            continue
                            
                        full_response.append(token)

                        # Limpieza en tiempo real del prefijo "Vector:" o "Vector," al inicio de la respuesta
                        if not prefix_cleared:
                            prefix_buffer += token
                            if len(prefix_buffer) >= 15 or "\n" in prefix_buffer:
                                cleaned_prefix = re.sub(r'^(Vector\s*[:,]?\s*\n*)+', '', prefix_buffer, flags=re.IGNORECASE).lstrip(" \r\n")
                                prefix_cleared = True
                                token = cleaned_prefix
                                if not token:
                                    continue
                            else:
                                continue

                        if strip_next_space:
                            token = token.lstrip(" \r\n")
                            if token:
                                strip_next_space = False

                        # Filtro inteligente de etiquetas de sistema en vuelo
                        # Evita emitir [PERCEPCIÓN...] o [MEMORIA...], pero preserva markdown links [texto](url) y código [0]
                        if in_bracket:
                            bracket_buffer += token
                            if "]" in bracket_buffer:
                                inside, after = bracket_buffer.split("]", 1)
                                is_sys = any(inside.upper().startswith(p) for p in SYSTEM_TAG_PREFIXES)
                                in_bracket = False
                                bracket_buffer = ""
                                if is_sys:
                                    remaining = after.lstrip(": \r\n")
                                    if remaining:
                                        yield f"data: {json.dumps({'token': remaining}, ensure_ascii=False)}\n\n"
                                    else:
                                        strip_next_space = True
                                else:
                                    yield f"data: {json.dumps({'token': f'[{inside}]{after}'}, ensure_ascii=False)}\n\n"
                            elif len(bracket_buffer) > 40 and not any(bracket_buffer.upper().startswith(p) for p in SYSTEM_TAG_PREFIXES):
                                # No coincide con prefijos de sistema, emitir buffer acumulado
                                yield f"data: {json.dumps({'token': bracket_buffer}, ensure_ascii=False)}\n\n"
                                in_bracket = False
                                bracket_buffer = ""
                            continue

                        if "[" in token and not in_bracket:
                            before, bracket_part = token.split("[", 1)
                            if before:
                                yield f"data: {json.dumps({'token': before}, ensure_ascii=False)}\n\n"
                    except Exception:
                        continue

        if not prefix_cleared and prefix_buffer:
            cleaned_prefix = re.sub(r'^(Vector\s*[:,]?\s*\n*)+', '', prefix_buffer, flags=re.IGNORECASE).lstrip(" \r\n")
            prefix_cleared = True
            if cleaned_prefix:
                yield f"data: {json.dumps({'token': cleaned_prefix}, ensure_ascii=False)}\n\n"

        if bracket_buffer and in_bracket:
            is_sys = any(bracket_buffer.upper().startswith(p) for p in SYSTEM_TAG_PREFIXES)
            if not is_sys:
                yield f"data: {json.dumps({'token': bracket_buffer}, ensure_ascii=False)}\n\n"

    except Exception as e:
        logger.error(f"[ChatStream] Error en streaming: {e}")
        err_msg = f"\n[Error de comunicación con motor local: {e}]"
        yield f"data: {json.dumps({'error': err_msg}, ensure_ascii=False)}\n\n"
        return

    # Al terminar la transmisión, sanitizar y guardar
    complete_text = "".join(full_response).strip()
    from ..views import sanitizar_respuesta_vector, dynamic_tool_generator
    clean_answer = sanitizar_respuesta_vector(complete_text)

    # Auto-guardado de herramientas en herramientas/ si el usuario solicitó crear código o función
    req_lower = raw_user_message.lower()
    pide_codigo = (
        any(p in req_lower for p in ["crea", "creame", "genera", "generame", "escribe", "escribeme", "hazme", "hace", "dame", "quiero", "necesito", "programa", "programame", "construye", "desarrolla"])
        and any(p in req_lower for p in ["codigo", "código", "funcion", "función", "script", "herramienta", "algoritmo", "programa", "modulo", "módulo"])
    ) or any(p in req_lower for p in ["guarda este codigo", "guardar codigo", "guardar herramienta", "guarda la herramienta"])
    
    if pide_codigo and "```python" in complete_text:
        try:
            match_code = re.search(r"```python\s*(.+?)\s*```", complete_text, re.DOTALL)
            if match_code:
                code_to_save = match_code.group(1).strip()
                func_match = re.search(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", code_to_save)
                tool_name = func_match.group(1) if func_match else f"tool_{datetime.now().strftime('%H%M%S')}"
                
                tool_res = dynamic_tool_generator.create_and_validate_tool(
                    tool_name, 
                    code_to_save, 
                    f"Código generado para: {raw_user_message[:80]}"
                )
                if tool_res.get("success"):
                    semantic_network.add_memory(
                        f"HERRAMIENTA CREADA: {tool_name} - Guardada en herramientas/{tool_name}.py",
                        "tool_creation"
                    )
                    tool_notice = f"\n\n🛠️ *[Herramienta '{tool_name}.py' guardada y validada en herramientas/]*"
                    yield f"data: {json.dumps({'token': tool_notice}, ensure_ascii=False)}\n\n"
                    clean_answer += tool_notice
        except Exception as te:
            logger.warning(f"[ChatStream] Aviso al auto-guardar herramienta: {te}")

    # Auto-diseño y graficación meteorológica en la respuesta de Vector si es consulta de clima
    es_clima = any("DATOS METEOROLÓGICOS" in m.get("content", "") for m in messages if isinstance(m, dict) and m.get("role") == "system")
    if es_clima and not ("| Indicador" in clean_answer or "| Indicadores" in clean_answer or "| Registro" in clean_answer):
        try:
            from .weather_service import generar_grafico_meteorologico_markdown
            sys_msg = next((m.get("content", "") for m in messages if isinstance(m, dict) and m.get("role") == "system"), "")
            match_ciu = re.search(r'DATOS METEOROLÓGICOS EN TIEMPO REAL \(([^)]+)\)', sys_msg)
            target_loc = match_ciu.group(1) if match_ciu else "Vicuña"
            grafico_extra = "\n\n" + generar_grafico_meteorologico_markdown(target_loc)
            yield f"data: {json.dumps({'token': grafico_extra}, ensure_ascii=False)}\n\n"
            clean_answer += grafico_extra
        except Exception as we_err:
            logger.warning(f"[ChatStream] Aviso adjuntando gráfico de clima: {we_err}")

    # Persistir en base de datos de forma limpia con session_id y user_name aislados
    if raw_user_message and clean_answer:
        try:
            Interaction.objects.create(
                user=user,
                question=raw_user_message,
                answer=clean_answer,
                session_id=session_id or "",
                user_name=user_name or ""
            )
        except Exception as se:
            logger.warning(f"[ChatStream] Aviso al persistir interacción: {se}")

    # Telemetría del optimizador de consultas
    try:
        elapsed = time.perf_counter() - t_start
        complexity = query_optimizer.classify_query(raw_user_message)
        query_optimizer.record_performance(complexity, elapsed)
        query_optimizer.cache_response(raw_user_message, clean_answer, complexity, user_name=user_name)
    except Exception as oe:
        logger.debug(f"[ChatStream] Aviso en registro de optimizador: {oe}")

    yield f"data: {json.dumps({'done': True, 'full_response': clean_answer, 'user_name': user_name, 'session_id': session_id}, ensure_ascii=False)}\n\n"
