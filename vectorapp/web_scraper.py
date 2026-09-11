"""
Módulo de Navegación, Extracción Web y Procesamiento de Enlaces para Vector.
Permite a Vector 'meterse a las páginas' que el usuario envía por enlace:
- Extrae metadatos, títulos, fechas de publicación ('capturar el día') y texto limpio de artículos y sitios web.
- Analiza enlaces de Google Maps para extraer nombres de lugares, coordenadas y zonas geográficas.
- Cero dependencias externas: utiliza la biblioteca estándar de Python (urllib, html.parser).
"""

import os
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Optional, Tuple


class SimpleHTMLTextExtractor(HTMLParser):
    """
    Extractor de texto y metadatos HTML ligero y seguro.
    Extrae título, descripción, fecha/día de publicación y cuerpo de texto omitiendo scripts/estilos.
    """
    def __init__(self):
        super().__init__()
        self.title = ""
        self.meta_desc = ""
        self.meta_date = ""
        self.in_title = False
        self.in_time = False
        self.ignore_tags = {'script', 'style', 'noscript', 'svg', 'header', 'footer', 'nav', 'iframe'}
        self.current_ignore = 0
        self.text_chunks = []

    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        attrs_dict = {k.lower(): v for k, v in attrs if k}
        
        if tag_lower in self.ignore_tags:
            self.current_ignore += 1
        elif tag_lower == 'title':
            self.in_title = True
        elif tag_lower == 'time':
            self.in_time = True
            if 'datetime' in attrs_dict and not self.meta_date:
                self.meta_date = attrs_dict['datetime']
        elif tag_lower == 'meta':
            name = attrs_dict.get('name', '').lower()
            prop = attrs_dict.get('property', '').lower()
            content = attrs_dict.get('content', '')
            if not content:
                return

            if name in ('description', 'twitter:description') or prop in ('og:description',):
                if not self.meta_desc:
                    self.meta_desc = content
            elif name in ('date', 'pubdate', 'publishdate', 'dc.date', 'article:published_time') or prop in ('article:published_time', 'og:published_time', 'og:article:published_time'):
                if not self.meta_date:
                    self.meta_date = content

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in self.ignore_tags and self.current_ignore > 0:
            self.current_ignore -= 1
        elif tag_lower == 'title':
            self.in_title = False
        elif tag_lower == 'time':
            self.in_time = False

    def handle_data(self, data):
        if self.current_ignore > 0:
            return
        if self.in_title:
            self.title += data
        else:
            text = data.strip()
            if text:
                if self.in_time and not self.meta_date:
                    self.meta_date = text
                self.text_chunks.append(text)

    def get_text(self) -> str:
        return " ".join(self.text_chunks)


def extraer_enlaces(texto: str) -> list[str]:
    """
    Encuentra todas las URLs HTTP/HTTPS presentes en el texto del mensaje.
    """
    if not texto:
        return []
    url_pattern = r'https?://[^\s<>"\')]+'
    return re.findall(url_pattern, texto)


def normalizar_lugar_chile(texto: str) -> str:
    """
    Normaliza nombres de lugares, comunas y sectores de la Región de Coquimbo y Chile.
    """
    t = texto.lower().strip()
    
    if "peñuelas" in t or "penuelas" in t:
        return "Peñuelas,Coquimbo,Chile"
    if "la serena" in t:
        return "La Serena,Chile"
    if "coquimbo" in t:
        return "Coquimbo,Chile"
    if "vicuña" in t or "vicuna" in t or "valle de elqui" in t or "valle del elqui" in t:
        return "Vicuña,Chile"
    if "paihuano" in t:
        return "Paihuano,Chile"
    if "pisco elqui" in t:
        return "Pisco Elqui,Chile"
    if "tierras blancas" in t:
        return "Tierras Blancas,Coquimbo,Chile"
    if "guanaqueros" in t:
        return "Guanaqueros,Chile"
    if "tongoy" in t:
        return "Tongoy,Chile"
    if "altovalsol" in t:
        return "Altovalsol,La Serena,Chile"
    if "montegrande" in t:
        return "Montegrande,Chile"
        
    c = t
    c = re.sub(r'\b(?:en\s+la\s+|en\s+)?(?:4(?:ta)?|cuarta)\s+regi[óo]n(?:\s+de\s+coquimbo)?\b', '', c, flags=re.IGNORECASE).strip()
    c = re.sub(r'\b(?:en\s+medio\s+de|entre)\s+[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+', '', c, flags=re.IGNORECASE).strip()
    c = re.sub(r'\b(?:por\s+esa\s+zona|por\s+la\s+zona|en\s+esa\s+zona)\b', '', c, flags=re.IGNORECASE).strip()
    c = re.sub(r'\b(?:allá|alla|ahí|ahi|allí|alli|acá|aca|aquí|aqui|afuera|hoy|ahora)\b', '', c, flags=re.IGNORECASE).strip()
    c = re.sub(r'\b(?:en\s+la|en\s+el|de\s+la|de\s+el|del|por|en)\s*$', '', c, flags=re.IGNORECASE).strip()
    
    return c.title() if c else "Vicuña,Chile"


def procesar_google_maps_url(url: str) -> dict:
    """
    Analiza un enlace de Google Maps extrayendo el lugar, coordenadas y zona.
    """
    final_url = url
    if "maps.app.goo.gl" in url or "goo.gl/maps" in url:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=4) as resp:
                final_url = resp.geturl()
        except Exception:
            pass

    lugar = ""
    coords = ""

    # Extraer nombre del lugar en /place/Nombre+Del+Lugar/
    m_place = re.search(r'/place/([^/@?#]+)', final_url)
    if m_place:
        raw_name = m_place.group(1).replace('+', ' ')
        lugar = urllib.parse.unquote(raw_name)
    elif "q=" in final_url:
        m_q = re.search(r'q=([^&]+)', final_url)
        if m_q:
            lugar = urllib.parse.unquote(m_q.group(1).replace('+', ' '))

    # Extraer coordenadas @lat,lon o en parámetros !3d...
    m_coords = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', final_url)
    if m_coords:
        coords = f"{m_coords.group(1)}, {m_coords.group(2)}"
    else:
        m_coords2 = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', final_url)
        if m_coords2:
            coords = f"{m_coords2.group(1)}, {m_coords2.group(2)}"

    sector = ""
    ciudad = ""
    lugar_lower = lugar.lower()
    if "peñuelas" in lugar_lower or "penuelas" in lugar_lower:
        sector = "Peñuelas"
        ciudad = "Coquimbo, Región de Coquimbo, Chile"
    elif "serena" in lugar_lower:
        ciudad = "La Serena, Región de Coquimbo, Chile"
    elif "coquimbo" in lugar_lower:
        ciudad = "Coquimbo, Región de Coquimbo, Chile"
    elif "vicuña" in lugar_lower or "vicuna" in lugar_lower:
        ciudad = "Vicuña, Región de Coquimbo, Chile"
    elif "paihuano" in lugar_lower:
        ciudad = "Paihuano, Valle del Elqui, Chile"
    else:
        ciudad = f"{lugar}, Chile" if lugar else "Chile"

    return {
        "tipo": "google_maps",
        "url": url,
        "lugar": lugar or "Ubicación en Google Maps",
        "sector": sector,
        "ciudad": ciudad,
        "coordenadas": coords,
        "query_clima": normalizar_lugar_chile(lugar or ciudad),
        "resumen": f"Ubicación en Google Maps identificada: {lugar}. Coordenadas: {coords or 'no especificadas'}. Zona geográfica: {ciudad}."
    }


def obtener_contenido_pagina_web(url: str, max_chars: int = 3500) -> dict:
    """
    Realiza una petición HTTP segura para extraer el contenido real de la página web.
    """
    if "google.com/maps" in url or "maps.app.goo.gl" in url or "goo.gl/maps" in url:
        return procesar_google_maps_url(url)

    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'es-CL,es;q=0.9,en;q=0.8'
            }
        )
        with urllib.request.urlopen(req, timeout=6) as response:
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text/html' not in content_type and 'application/xhtml' not in content_type and 'text/plain' not in content_type:
                return {
                    "tipo": "archivo_externo",
                    "url": url,
                    "titulo": os.path.basename(url) or "Archivo",
                    "fecha": "",
                    "contenido": f"[Recurso binario o no HTML: {content_type}]"
                }

            charset = 'utf-8'
            if 'charset=' in content_type:
                charset = content_type.split('charset=')[-1].split(';')[0].strip()

            raw_bytes = response.read(180000)
            try:
                html_text = raw_bytes.decode(charset, errors='replace')
            except Exception:
                html_text = raw_bytes.decode('utf-8', errors='replace')

        parser = SimpleHTMLTextExtractor()
        parser.feed(html_text)

        titulo = parser.title.strip() or parser.meta_desc[:60] or "Página Web"
        texto_limpio = " ".join(parser.text_chunks)
        texto_limpio = re.sub(r'\s+', ' ', texto_limpio).strip()

        return {
            "tipo": "pagina_web",
            "url": url,
            "titulo": titulo,
            "descripcion": parser.meta_desc.strip(),
            "fecha": parser.meta_date.strip(),
            "contenido": texto_limpio[:max_chars]
        }
    except Exception as e:
        return {
            "tipo": "error_carga",
            "url": url,
            "titulo": "Error accediendo a página",
            "fecha": "",
            "contenido": f"No se pudo cargar la página ({str(e)})."
        }


def procesar_enlaces_mensaje(mensaje: str) -> Tuple[str, Optional[dict]]:
    """
    Inspecciona el mensaje del usuario en busca de enlaces URL.
    Si encuentra enlaces, se 'mete a la página', extrae su contenido o ubicación de mapas,
    y genera un bloque de contexto formateado para el System Prompt.
    """
    enlaces = extraer_enlaces(mensaje)
    if not enlaces:
        return "", None

    # Procesar el enlace principal (primer enlace encontrado)
    primer_enlace = enlaces[0]
    info = obtener_contenido_pagina_web(primer_enlace)

    if info.get("tipo") == "google_maps":
        bloque_contexto = (
            f"\nENLACE DE UBICACIÓN IDENTIFICADO (GOOGLE MAPS):\n"
            f"- URL: {info['url']}\n"
            f"- Lugar detectado: {info['lugar']}\n"
            f"- Sector / Comuna: {info['sector'] or info['ciudad']}\n"
            f"- Coordenadas: {info['coordenadas'] or 'Disponibles en el enlace'}\n"
            f"- Zona base: {info['ciudad']}\n\n"
            f"DIRECTIVA DE UBICACIÓN DE MAPAS:\n"
            f"Sebastian te ha compartido un enlace de Google Maps con la ubicación '{info['lugar']}'. "
            f"Reconoce esta ubicación como la zona de interés actual para cualquier consulta de hora, geografía o clima en esa área.\n"
        )
        return bloque_contexto, info

    fecha_str = f"- Fecha / Día detectado: {info['fecha']}\n" if info.get('fecha') else ""
    desc_str = f"- Descripción: {info['descripcion']}\n" if info.get('descripcion') else ""
    
    bloque_contexto = (
        f"\nCONTENIDO DE LA PÁGINA WEB VINCULADA POR EL INTERLOCUTOR:\n"
        f"- URL: {info['url']}\n"
        f"- Título: {info['titulo']}\n"
        f"{fecha_str}"
        f"{desc_str}"
        f"- Contenido extraído del sitio:\n"
        f"\"\"\"\n{info['contenido']}\n\"\"\"\n\n"
        f"DIRECTIVA DE PÁGINA WEB:\n"
        f"Se te ha enviado este enlace para que te metas a la página y analices su contenido. "
        f"Utiliza este texto para responder, capturar el día/fecha, resumir o explicar lo que se te pregunte sobre él.\n"
    )
    return bloque_contexto, info


def extraer_articulo_profundo(url: str, max_chars: int = 4500) -> dict:
    """
    Extracción profunda de un artículo o página web al estilo Copilot.
    Extrae título, metadatos, fecha de publicación y texto limpio.
    """
    return obtener_contenido_pagina_web(url, max_chars=max_chars)


def investigar_multisitio_chile(query: str, max_fuentes: int = 4) -> dict:
    """
    Investiga activamente en múltiples fuentes en internet con priorización regional para Chile (.cl).
    Retorna un compendio estructurado de fuentes, extractos limpios y fechas para debate y síntesis.
    """
    from duckduckgo_search import DDGS

    chile_query = query
    chile_keywords = ['chile', 'coquimbo', 'serena', 'santiago', 'valparaíso', 'vicuña', 'elqui', 'antofagasta', 'concepción']
    if not any(k in query.lower() for k in chile_keywords):
        chile_query = f"{query} Chile"

    fuentes = []
    try:
        ddgs = DDGS()
        results = list(ddgs.text(chile_query, region='cl-es', max_results=max_fuentes * 2))

        # Priorizar fuentes con dominio .cl o medios nacionales/regionales conocidos
        prioritarias = []
        secundarias = []
        for r in results:
            url = r.get('href', '')
            if '.cl/' in url or url.endswith('.cl') or any(m in url for m in ['emol', 'biobiochile', 'latercera', 'cooperativa', 'meteored.cl', 'elmostrador', '24horas', 't13']):
                prioritarias.append(r)
            else:
                secundarias.append(r)

        seleccionadas = (prioritarias + secundarias)[:max_fuentes]

        for item in seleccionadas:
            url = item.get('href', '')
            title = item.get('title', '')
            snippet = item.get('body', '')

            # Extraer contenido real del sitio web
            web_info = obtener_contenido_pagina_web(url, max_chars=1800)
            texto_real = web_info.get('contenido', '')

            fuentes.append({
                "titulo": title or web_info.get('titulo', ''),
                "url": url,
                "snippet": snippet,
                "fecha": web_info.get('fecha', ''),
                "contenido_limpio": texto_real if len(texto_real) > 150 else snippet,
                "es_chileno": ('.cl' in url) or any(m in url for m in ['chile', 'coquimbo', 'serena', 'emol', 'biobio'])
            })

    except Exception as e:
        return {
            "success": False,
            "query": query,
            "error": str(e),
            "fuentes": []
        }

    return {
        "success": True,
        "query": query,
        "total_fuentes": len(fuentes),
        "fuentes": fuentes
    }

