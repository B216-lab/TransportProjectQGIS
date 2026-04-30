"""
Геометрические утилиты для работы с барьерами
Перенесено из js/barriers.js
"""

from typing import List, Dict, Any, Optional
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.ops import unary_union
import json

class GeometryUtils:
    """
    Класс для геометрических операций с барьерами
    """
    
    def __init__(self):
        self.barrier_geometries = []
    
    def find_barrier_polygon_for_point(self, point: Dict, barriers: List[Dict]) -> Optional[Polygon]:
        """
        Находит барьерный полигон, содержащий точку
        Перенесено из findBarrierPolygonForPoint()
        
        Args:
            point: Точка {'lng': x, 'lat': y}
            barriers: Список барьерных полигонов в GeoJSON формате
        
        Returns:
            Polygon или None: Барьерный полигон
        """
        pt = Point(point['lng'], point['lat'])
        
        for barrier in barriers:
            polygon = self._geojson_to_shapely(barrier)
            if polygon and (polygon.contains(pt) or polygon.touches(pt)):
                return polygon
        
        return None
    
    def group_points_by_barriers(self, points: List[Dict], barriers: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Группирует точки по барьерным полигонам
        Перенесено из groupPointsByBarriers()
        
        Args:
            points: Список точек
            barriers: Список барьерных полигонов
        
        Returns:
            Dict: Группы точек
        """
        groups = {}
        
        # Конвертируем барьеры в Shapely объекты
        barrier_polygons = []
        for barrier in barriers:
            polygon = self._geojson_to_shapely(barrier)
            if polygon:
                barrier_polygons.append(polygon)
        
        for point in points:
            pt = Point(point['lng'], point['lat'])
            found = False
            
            # Ищем в каком барьере точка
            for i, barrier in enumerate(barrier_polygons):
                if barrier.contains(pt) or barrier.touches(pt):
                    group_key = f"barrier_{i}"
                    if group_key not in groups:
                        groups[group_key] = []
                    groups[group_key].append(point)
                    found = True
                    break
            
            if not found:
                if "outside" not in groups:
                    groups["outside"] = []
                groups["outside"].append(point)
        
        return groups
    
    def is_point_in_barrier(self, point: Dict, barrier_polygon: Polygon) -> bool:
        """
        Проверяет, находится ли точка внутри барьерного полигона
        """
        pt = Point(point['lng'], point['lat'])
        return barrier_polygon.contains(pt) or barrier_polygon.touches(pt)
    
    def get_barrier_stats(self, barriers: List[Dict]) -> Dict:
        """
        Получает статистику по барьерам
        """
        stats = {
            'total_barriers': len(barriers),
            'total_area': 0,
            'barrier_types': {}
        }
        
        for barrier in barriers:
            polygon = self._geojson_to_shapely(barrier)
            if polygon:
                area = polygon.area * (111 * 111)  # Конвертация в км²
                stats['total_area'] += area
                
                # Определяем тип барьера
                barrier_type = barrier.get('properties', {}).get('type', 'unknown')
                stats['barrier_types'][barrier_type] = stats['barrier_types'].get(barrier_type, 0) + 1
        
        return stats
    
    def merge_barriers(self, barriers: List[Dict]) -> Optional[Polygon]:
        """
        Объединяет все барьеры в один полигон
        """
        polygons = []
        for barrier in barriers:
            polygon = self._geojson_to_shapely(barrier)
            if polygon:
                polygons.append(polygon)
        
        if polygons:
            return unary_union(polygons)
        return None
    
    def _geojson_to_shapely(self, geojson: Dict) -> Optional[Polygon]:
        """
        Конвертирует GeoJSON в Shapely полигон
        """
        try:
            # Извлекаем геометрию
            if geojson.get('type') == 'Feature':
                geom = geojson.get('geometry', {})
            else:
                geom = geojson
            
            # Обрабатываем разные типы геометрий
            if geom.get('type') == 'Polygon':
                coords = geom.get('coordinates', [])
                if coords:
                    return Polygon(coords[0])
            
            elif geom.get('type') == 'MultiPolygon':
                coords = geom.get('coordinates', [])
                if coords and coords[0]:
                    return Polygon(coords[0][0])
            
            elif geom.get('type') == 'GeometryCollection':
                # Берем первый полигон из коллекции
                for g in geom.get('geometries', []):
                    if g.get('type') == 'Polygon':
                        coords = g.get('coordinates', [])
                        if coords:
                            return Polygon(coords[0])
        
        except Exception as e:
            print(f"Ошибка конвертации GeoJSON: {e}")
        
        return None
    
    def calculate_distance_meters(self, point1: Dict, point2: Dict) -> float:
        """
        Рассчитывает расстояние между двумя точками в метрах
        Использует формулу гаверсинуса
        """
        from math import radians, sin, cos, sqrt, atan2
        
        lat1 = radians(point1['lat'])
        lon1 = radians(point1['lng'])
        lat2 = radians(point2['lat'])
        lon2 = radians(point2['lng'])
        
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        # Радиус Земли в метрах
        R = 6371000
        distance = R * c
        
        return distance