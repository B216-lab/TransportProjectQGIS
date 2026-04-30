"""
Двигатель кластеризации с учетом барьеров
Перенесено из js/clustering.js
"""

import numpy as np
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from shapely.geometry import Point, Polygon
from sklearn.cluster import KMeans, DBSCAN
import math

class ClusteringEngine:
    """
    Класс для выполнения кластеризации точек с учетом барьерных полигонов
    """
    
    def __init__(self):
        self.barrier_geometries = []
    
    def kmeans_with_barriers(self, points: List[Dict], k: int, barriers: List[Dict]) -> List[int]:
        """
        K-means кластеризация с учетом барьеров
        Перенесено из kMeansWithBarriers()
        
        Args:
            points: Список точек [{'lng': x, 'lat': y, 'population': pop}, ...]
            k: Количество кластеров
            barriers: Список барьерных полигонов в GeoJSON формате
        
        Returns:
            List[int]: Метки кластеров для каждой точки
        """
        # Группируем точки по барьерам
        groups = self._group_points_by_barriers(points, barriers)
        
        all_labels = [-1] * len(points)
        global_cluster_offset = 0
        
        for group_key, group_points in groups.items():
            if len(group_points) == 0:
                continue
            
            # Определяем количество кластеров для этой группы
            n_clusters = min(k, max(1, len(group_points) // 5))
            
            if n_clusters <= 1 or len(group_points) < n_clusters:
                # Все точки группы в один кластер
                for i, point in enumerate(group_points):
                    original_idx = self._find_point_index(points, point)
                    if original_idx != -1:
                        all_labels[original_idx] = global_cluster_offset
                global_cluster_offset += 1
                continue
            
            # Подготовка координат для кластеризации
            coords = [[p['lng'], p['lat']] for p in group_points]
            labels = self._kmeans_clustering(coords, n_clusters)
            
            # Присваиваем глобальные метки
            for i, point in enumerate(group_points):
                original_idx = self._find_point_index(points, point)
                if original_idx != -1:
                    all_labels[original_idx] = global_cluster_offset + labels[i]
            
            global_cluster_offset += n_clusters
        
        # Перенумеровываем кластеры последовательно
        return self._renumber_clusters(all_labels)
    
    def dbscan_with_barriers(self, points: List[Dict], epsilon: float, min_samples: int, barriers: List[Dict]) -> List[int]:
        """
        DBSCAN кластеризация с учетом барьеров
        Перенесено из dbscanWithBarriers()
        
        Args:
            points: Список точек [{'lng': x, 'lat': y, 'population': pop}, ...]
            epsilon: Радиус поиска в метрах
            min_samples: Минимальное количество точек для кластера
            barriers: Список барьерных полигонов в GeoJSON формате
        
        Returns:
            List[int]: Метки кластеров для каждой точки (-1 = шум)
        """
        # Группируем точки по барьерам
        groups = self._group_points_by_barriers(points, barriers)
        
        all_labels = [-1] * len(points)
        global_cluster_offset = 0
        
        for group_key, group_points in groups.items():
            if len(group_points) < min_samples:
                # Недостаточно точек для кластера - помечаем как шум
                for point in group_points:
                    original_idx = self._find_point_index(points, point)
                    if original_idx != -1:
                        all_labels[original_idx] = -1
                continue
            
            # Подготовка координат
            coords = [[p['lng'], p['lat']] for p in group_points]
            labels = self._dbscan_clustering(coords, epsilon, min_samples)
            
            # Находим максимальную метку в этой группе
            max_local_label = max(labels) if labels else -1
            
            # Присваиваем глобальные метки
            for i, point in enumerate(group_points):
                original_idx = self._find_point_index(points, point)
                if original_idx != -1:
                    if labels[i] == -1:
                        all_labels[original_idx] = -1
                    else:
                        all_labels[original_idx] = global_cluster_offset + labels[i]
            
            if max_local_label > -1:
                global_cluster_offset += (max_local_label + 1)
        
        # Перенумеровываем кластеры и удаляем шум
        return self._renumber_clusters(all_labels, keep_noise=True)
    
    def _group_points_by_barriers(self, points: List[Dict], barriers: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Группирует точки по барьерным полигонам
        Перенесено из groupPointsByBarriers()
        
        Args:
            points: Список точек
            barriers: Список барьерных полигонов в GeoJSON формате
        
        Returns:
            Dict: Группы точек {group_key: [points]}
        """
        groups = defaultdict(list)
        
        # Конвертируем барьеры в Shapely полигоны
        barrier_polygons = []
        for barrier in barriers:
            try:
                polygon = self._geojson_to_shapely(barrier)
                if polygon:
                    barrier_polygons.append(polygon)
            except Exception as e:
                print(f"Ошибка конвертации барьера: {e}")
                continue
        
        for point in points:
            pt = Point(point['lng'], point['lat'])
            found_barrier = None
            
            # Ищем в каком барьере находится точка
            for i, barrier in enumerate(barrier_polygons):
                if barrier.contains(pt) or barrier.touches(pt):
                    found_barrier = i
                    break
            
            if found_barrier is not None:
                group_key = f"barrier_{found_barrier}"
            else:
                group_key = "outside"
            
            groups[group_key].append(point)
        
        return dict(groups)
    
    def _kmeans_clustering(self, coords: List[List[float]], k: int) -> List[int]:
        """
        Базовый K-means алгоритм
        Перенесено из kMeansClustering()
        
        Args:
            coords: Список координат [[lng, lat], ...]
            k: Количество кластеров
        
        Returns:
            List[int]: Метки кластеров
        """
        if len(coords) < k:
            k = len(coords)
        
        if k == 0:
            return [0] * len(coords)
        
        # Преобразуем в numpy массив
        X = np.array(coords)
        
        # Используем sklearn KMeans
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X)
        
        return labels.tolist()
    
    def _dbscan_clustering(self, coords: List[List[float]], epsilon: float, min_samples: int) -> List[int]:
        """
        Базовый DBSCAN алгоритм с учетом расстояния в метрах
        Перенесено из dbscanClustering()
        
        Args:
            coords: Список координат [[lng, lat], ...]
            epsilon: Радиус поиска в метрах
            min_samples: Минимальное количество точек для кластера
        
        Returns:
            List[int]: Метки кластеров (-1 = шум)
        """
        if len(coords) < min_samples:
            return [-1] * len(coords)
        
        # Конвертируем градусы в метры для DBSCAN
        # Для малых расстояний можно использовать приближение
        # 1 градус ≈ 111 км = 111000 метров
        epsilon_degrees = epsilon / 111000.0
        
        X = np.array(coords)
        dbscan = DBSCAN(eps=epsilon_degrees, min_samples=min_samples, metric='euclidean')
        labels = dbscan.fit_predict(X)
        
        return labels.tolist()
    
    def _geojson_to_shapely(self, geojson: Dict) -> Polygon:
        """
        Конвертирует GeoJSON в Shapely полигон
        """
        try:
            if geojson.get('type') == 'Feature':
                geom = geojson.get('geometry', {})
            else:
                geom = geojson
            
            if geom.get('type') == 'Polygon':
                coords = geom.get('coordinates', [])
                if coords:
                    return Polygon(coords[0])
            elif geom.get('type') == 'MultiPolygon':
                # Берем первый полигон из мультиполигона
                coords = geom.get('coordinates', [])
                if coords and coords[0]:
                    return Polygon(coords[0][0])
        except Exception as e:
            print(f"Ошибка конвертации GeoJSON: {e}")
        
        return None
    
    def _find_point_index(self, points: List[Dict], target_point: Dict) -> int:
        """
        Находит индекс точки в списке
        """
        for i, point in enumerate(points):
            if (point['lng'] == target_point['lng'] and 
                point['lat'] == target_point['lat']):
                return i
        return -1
    
    def _renumber_clusters(self, labels: List[int], keep_noise: bool = False) -> List[int]:
        """
        Перенумеровывает кластеры последовательно от 0
        """
        if not labels:
            return labels
        
        unique_clusters = sorted(set(labels))
        
        # Убираем шум (-1) из перенумерации если нужно
        if not keep_noise and -1 in unique_clusters:
            unique_clusters.remove(-1)
        
        # Создаем маппинг старых индексов на новые
        mapping = {}
        for i, cluster in enumerate(unique_clusters):
            mapping[cluster] = i
        
        # Если нужно сохранить шум
        if keep_noise and -1 in labels:
            mapping[-1] = -1
        
        # Применяем маппинг
        return [mapping[label] for label in labels]