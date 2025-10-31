"""
Denormalization module for transforming MySQL publications to Elasticsearch documents
Flattens all JOINs into a single document
"""

import os
from database import mysql_query
import logging

logger = logging.getLogger(__name__)

def denormalize_publication(publicacion_id):
    """
    Fetch publication from MySQL with all JOINs and denormalize into ES document
    
    Args:
        publicacion_id: ID of publication to fetch
        
    Returns:
        dict: Elasticsearch document with all denormalized data
    """
    try:
        # Query MySQL with all JOINs
        query = """
            SELECT 
                p.*,
                GROUP_CONCAT(DISTINCT tp.tag) as tag_ids_raw,
                GROUP_CONCAT(DISTINCT CONCAT(t.id, ':', COALESCE(t.descripcion, ''))) as tags_raw,
                pa.nombre as pais_nombre,
                pa.id as pais_id,
                GROUP_CONCAT(DISTINCT sm.mercado_id) as mercado_ids_raw,
                ptl.tipo_licit_id_esAR,
                ptl.tipo_licit_id_ptBR,
                ptl.tipo_licit_id_enUS,
                d.tasaCambioUSD,
                (CASE WHEN p.apertura >= UTC_TIMESTAMP() THEN 1 ELSE 0 END) as vigente
            FROM publicaciones p
            LEFT JOIN tags_publicaciones tp ON p.id = tp.publicacion
            LEFT JOIN tags t ON tp.tag = t.id AND t.usuario IS NULL
            LEFT JOIN paises pa ON (
                CASE 
                    WHEN p.pais REGEXP '^[0-9]+$' THEN pa.id = CAST(p.pais AS UNSIGNED)
                    ELSE pa.nombre = p.pais
                END
            )
            LEFT JOIN scrapers_mercados sm ON p.scraper = sm.scraper_id
            LEFT JOIN publicaciones_tipos_licit ptl ON p.tipo_id = ptl.id
            LEFT JOIN divisas d ON p.divisaSimboloISO = d.SimboloISO
            WHERE p.id = %s
            GROUP BY p.id
        """
        
        results = mysql_query(query, (publicacion_id,))
        
        if not results or len(results) == 0:
            logger.warning(f"Publication {publicacion_id} not found")
            return None
        
        pub = results[0]
        
        # Parse tag_ids
        tag_ids = []
        if pub.get('tag_ids_raw'):
            tag_ids = [int(t) for t in str(pub['tag_ids_raw']).split(',') if t.strip().isdigit()]
        
        # Parse tags array
        tags = []
        if pub.get('tags_raw'):
            tags_raw = str(pub['tags_raw']).split(',')
            for tag_str in tags_raw:
                if ':' in tag_str:
                    parts = tag_str.split(':', 1)
                    if len(parts) == 2 and parts[0].isdigit():
                        tags.append({
                            'id': int(parts[0]),
                            'descripcion': parts[1] or ''
                        })
        
        # Parse mercado_ids
        mercado_ids = []
        if pub.get('mercado_ids_raw'):
            mercado_ids = [int(m) for m in str(pub['mercado_ids_raw']).split(',') if m.strip().isdigit()]
        
        # Helper function to validate dates (MySQL sometimes returns '0000-00-00 00:00:00')
        def validate_date(date_value):
            if not date_value:
                return None
            date_str = str(date_value)
            # Check for invalid MySQL dates
            if date_str.startswith('0000-00-00') or date_str == 'None' or date_str == '':
                return None
            return date_value
        
        # Helper function to parse monto from format like '$3.900.000,00'
        def parse_monto(monto_value):
            if not monto_value:
                return None
            if isinstance(monto_value, (int, float)):
                return float(monto_value)
            
            monto_str = str(monto_value).strip()
            if not monto_str or monto_str == '' or monto_str == '0':
                return None
            
            # Remove currency symbols and clean format
            # Format: $3.900.000,00 or $3.900.000,50
            # Remove $, spaces, and dots (thousands separator)
            cleaned = monto_str.replace('$', '').replace(' ', '').replace('.', '')
            
            # Replace comma (decimal separator) with dot
            cleaned = cleaned.replace(',', '.')
            
            try:
                result = float(cleaned)
                logger.debug(f"Parsed monto: '{monto_str}' -> {result}")
                return result
            except (ValueError, TypeError) as e:
                # If can't parse, log warning and return None (will be excluded from doc)
                logger.warning(f"Failed to parse monto '{monto_str}' -> cleaned: '{cleaned}': {str(e)}")
                return None
        
        # Parse monto first
        monto_parsed = parse_monto(pub.get('monto'))
        
        # Build Elasticsearch document
        doc = {
            # All publication fields
            'id': pub.get('id'),
            'scraper': pub.get('scraper'),
            'idexterno': pub.get('idexterno'),
            'referencia': pub.get('referencia'),
            'objeto': pub.get('objeto'),
            'agencia': pub.get('agencia'),
            'oficina': pub.get('oficina'),
            'link': pub.get('link'),
            'publicado': validate_date(pub.get('publicado')),
            'actualizado': validate_date(pub.get('actualizado')),
            'apertura': validate_date(pub.get('apertura')),
            'cierre': validate_date(pub.get('cierre')),
            'pais': pub.get('pais'),
            'rubro': pub.get('rubro'),
            'subrubro': pub.get('subrubro'),
            'tipo': pub.get('tipo'),
            'tipo_id': pub.get('tipo_id'),
            'tipo_cliente_id': pub.get('tipo_cliente_id'),
            'contacto': pub.get('contacto'),
            'observaciones': pub.get('observaciones'),
            'categoria': pub.get('categoria'),
            'cargado': validate_date(pub.get('cargado')),
            'editado': validate_date(pub.get('editado')),
            'visible': bool(int(pub.get('visible') or 0)) if pub.get('visible') is not None else None,
            'attachs': pub.get('attachs'),
            'monto': monto_parsed,
            'divisaSimboloISO': pub.get('divisaSimboloISO'),
            
            # Denormalized fields
            'tag_ids': tag_ids,
            'tags': tags,
            'pais_nombre': pub.get('pais_nombre'),
            'pais_id': pub.get('pais_id'),
            'mercado_ids': mercado_ids,
            'tipo_licit_ids': {
                'esAR': pub.get('tipo_licit_id_esAR'),
                'ptBR': pub.get('tipo_licit_id_ptBR'),
                'enUS': pub.get('tipo_licit_id_enUS')
            },
            'tasaCambioUSD': float(pub.get('tasaCambioUSD') or 0),
            'vigente': bool(pub.get('vigente') or 0)
        }
        
        # Remove None values
        doc = {k: v for k, v in doc.items() if v is not None}
        
        return doc
        
    except Exception as e:
        logger.error(f"Failed to denormalize publication {publicacion_id}: {str(e)}")
        raise

def get_publication_from_mysql(publicacion_id):
    """
    Get single publication from MySQL with all JOINs
    """
    return denormalize_publication(publicacion_id)

def get_publications_from_scraper(scraper_id, since_time, limit=1000):
    """
    Get publications from a scraper updated since given time
    
    Args:
        scraper_id: ID of scraper
        since_time: Datetime string (YYYY-MM-DD HH:MM:SS)
        limit: Maximum number of publications to return
        
    Returns:
        list: List of publication IDs
    """
    try:
        query = """
            SELECT id FROM publicaciones 
            WHERE scraper = %s 
            AND (cargado >= %s OR editado >= %s)
            AND visible = 1
            ORDER BY editado DESC, id DESC
            LIMIT %s
        """
        
        results = mysql_query(query, (scraper_id, since_time, since_time, limit))
        return [row['id'] for row in results] if results else []
        
    except Exception as e:
        logger.error(f"Failed to get publications from scraper {scraper_id}: {str(e)}")
        return []

def get_publications_since(since_time, limit=5000):
    """
    Get all publications updated since given time
    
    Args:
        since_time: Datetime string (YYYY-MM-DD HH:MM:SS)
        limit: Maximum number of publications to return
        
    Returns:
        list: List of publication IDs
    """
    try:
        query = """
            SELECT id FROM publicaciones 
            WHERE (cargado >= %s OR editado >= %s)
            AND visible = 1
            ORDER BY editado DESC, id DESC
            LIMIT %s
        """
        
        results = mysql_query(query, (since_time, since_time, limit))
        return [row['id'] for row in results] if results else []
        
    except Exception as e:
        logger.error(f"Failed to get publications since {since_time}: {str(e)}")
        return []

def get_all_publication_ids(batch_size=1000, offset=0):
    """
    Get all publication IDs in batches for bulk indexing
    
    Args:
        batch_size: Number of IDs per batch
        offset: Starting offset
        
    Returns:
        list: List of publication IDs
    """
    try:
        query = """
            SELECT id FROM publicaciones 
            WHERE visible = 1
            ORDER BY id ASC
            LIMIT %s OFFSET %s
        """
        
        results = mysql_query(query, (batch_size, offset))
        return [row['id'] for row in results] if results else []
        
    except Exception as e:
        logger.error(f"Failed to get publication IDs batch: {str(e)}")
        return []

