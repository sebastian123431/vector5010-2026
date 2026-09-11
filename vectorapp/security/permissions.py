"""
Sistema de permisos granulares para herramientas dinámicas de VECTOR 2026.
Implementa el principio de privilegio mínimo (least privilege) y deny by default.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

@dataclass
class ToolPermissions:
    """
    Permisos explícitos que definen qué capacidades tiene autorizadas una herramienta.
    Por defecto todas las capacidades están desactivadas (False).
    """
    filesystem_read: bool = False
    filesystem_write: bool = False
    network: bool = False
    database: bool = False
    system_info: bool = False

    def to_dict(self) -> Dict[str, bool]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> 'ToolPermissions':
        if not data or not isinstance(data, dict):
            return cls()
        return cls(
            filesystem_read=bool(data.get('filesystem_read', False)),
            filesystem_write=bool(data.get('filesystem_write', False)),
            network=bool(data.get('network', False)),
            database=bool(data.get('database', False)),
            system_info=bool(data.get('system_info', False))
        )

    @classmethod
    def default_for_category(cls, category: str) -> 'ToolPermissions':
        """
        Asigna el perfil de permisos mínimo necesario según la categoría declarada.
        """
        cat = (category or "").lower().strip()
        if cat in ('calculations', 'matematicas', 'math', 'calculator'):
            return cls(filesystem_read=False, filesystem_write=False, network=False, database=False, system_info=False)
        elif cat in ('time_related', 'tiempo', 'time', 'date', 'calendar'):
            return cls(filesystem_read=False, filesystem_write=False, network=False, database=False, system_info=False)
        elif cat in ('file_operations', 'archivos', 'file', 'csv', 'document'):
            return cls(filesystem_read=True, filesystem_write=True, network=False, database=False, system_info=False)
        elif cat in ('data_processing', 'datos', 'data'):
            return cls(filesystem_read=True, filesystem_write=False, network=False, database=False, system_info=False)
        elif cat in ('web_scraping', 'web', 'internet', 'scraping', 'api_integration'):
            return cls(filesystem_read=False, filesystem_write=False, network=True, database=False, system_info=False)
        elif cat in ('database', 'base de datos', 'sql'):
            return cls(filesystem_read=False, filesystem_write=False, network=False, database=True, system_info=False)
        elif cat in ('monitoring', 'system_info', 'sistema'):
            return cls(filesystem_read=False, filesystem_write=False, network=False, database=False, system_info=True)
        else:
            # Categoría general o desconocida: privilegios mínimos
            return cls(filesystem_read=False, filesystem_write=False, network=False, database=False, system_info=False)
