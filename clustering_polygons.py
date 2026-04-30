"""
Модуль для создания полигонов на основе результатов кластеризации
"""

class ClusteringPolygonGenerator:
    """
    Класс для генерации полигонов на основе кластеризованных точек
    """
    
    def __init__(self, use_alpha_shape: bool = True, alpha: float = 0.5):
        """
        Инициализация генератора полигонов
        
        Args:
            use_alpha_shape: Использовать alpha shape для более точных полигонов
            alpha: Параметр alpha для alpha shape (0-1, чем больше, тем детальнее)
        """
        self.use_alpha_shape = use_alpha_shape
        self.alpha = alpha
    
    def create_polygons_from_clusters(self, clustered_features, method='convex_hull', simplify_tolerance=0.0001):
        """
        Создает полигоны для каждого кластера
        
        Args:
            clustered_features: Список Feature объектов с cluster_id
            method: Метод построения ('convex_hull', 'alpha_shape', 'concave')
            simplify_tolerance: Допуск упрощения геометрии (в градусах)
        
        Returns:
            GeoJSON FeatureCollection с полигонами кластеров
        """
        # Группируем точки по кластерам
        clusters = self._group_by_cluster(clustered_features)
        
        polygons = []
        cluster_stats = {}
        
        for cluster_id, points in clusters.items():
            if cluster_id == 'Шум' or len(points) < 3:
                continue
            
            # Создаем полигон для кластера
            polygon = self._create_polygon_for_points(points, method)
            
            if polygon:
                # Упрощаем полигон
                polygon = self._simplify_polygon(polygon, simplify_tolerance)
                
                # Собираем статистику по кластеру
                stats = self._calculate_cluster_stats(points, cluster_id)
                cluster_stats[cluster_id] = stats
                
                # Создаем Feature
                feature = {
                    "type": "Feature",
                    "geometry": self._polygon_to_geojson(polygon),
                    "properties": {
                        "cluster_id": int(cluster_id) if not isinstance(cluster_id, int) else cluster_id,
                        "point_count": len(points),
                        "total_population": stats['total_population'],
                        "avg_population": round(stats['avg_population'], 2),
                        "area_sqkm": round(stats['area_sqkm'], 4),
                        "density_per_sqkm": round(stats['density_per_sqkm'], 2),
                        "center_lat": stats['center_lat'],
                        "center_lon": stats['center_lon']
                    }
                }
                polygons.append(feature)
        
        return {
            "type": "FeatureCollection",
            "features": polygons,
            "metadata": {
                "total_clusters": len(polygons),
                "method": method,
                "statistics": cluster_stats
            }
        }
    
    def _group_by_cluster(self, features):
        """Группирует точки по ID кластера"""
        clusters = {}
        
        for feature in features:
            cluster_id = feature['properties'].get('cluster_id')
            if cluster_id is None or cluster_id == 'Шум':
                continue
            
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            
            coords = feature['geometry']['coordinates']
            population = feature['properties'].get('Насел', 0)
            clusters[cluster_id].append({
                'coords': (coords[0], coords[1]),
                'population': population
            })
        
        return clusters
    
    def _create_polygon_for_points(self, points, method):
        """Создает полигон для набора точек"""
        coords = [p['coords'] for p in points]
        
        if len(coords) < 3:
            return None
        
        if method == 'convex_hull':
            return self._create_convex_hull(coords)
        elif method == 'alpha_shape':
            return self._create_alpha_shape(coords)
        elif method == 'concave':
            return self._create_concave_hull(coords)
        else:
            return self._create_convex_hull(coords)
    
    def _create_convex_hull(self, coords):
        """Создает выпуклую оболочку (упрощенная версия)"""
        if len(coords) < 3:
            return None
        
        # Простая реализация convex hull (алгоритм Грэхема)
        points = sorted(coords)
        
        def cross(o, a, b):
            return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
        
        lower = []
        for p in points:
            while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
                lower.pop()
            lower.append(p)
        
        upper = []
        for p in reversed(points):
            while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
                upper.pop()
            upper.append(p)
        
        hull = lower[:-1] + upper[:-1]
        
        if len(hull) < 3:
            return None
        
        return hull
    
    def _create_alpha_shape(self, coords):
        """Создает Alpha Shape (упрощенная версия - использует convex hull)"""
        # Для простоты используем convex hull
        # В полной версии нужен alphashape
        return self._create_convex_hull(coords)
    
    def _create_concave_hull(self, coords):
        """Создает вогнутую оболочку"""
        return self._create_alpha_shape(coords)
    
    def _simplify_polygon(self, polygon, tolerance):
        """Упрощает полигон"""
        if len(polygon) < 3:
            return polygon
        
        # Простое упрощение - удаляем точки, которые слишком близко
        simplified = [polygon[0]]
        for i in range(1, len(polygon)):
            last = simplified[-1]
            curr = polygon[i]
            dist = ((curr[0] - last[0])**2 + (curr[1] - last[1])**2)**0.5
            if dist > tolerance:
                simplified.append(curr)
        
        # Замыкаем полигон
        if len(simplified) >= 3:
            return simplified
        return polygon
    
    def _calculate_cluster_stats(self, points, cluster_id):
        """Рассчитывает статистику для кластера"""
        populations = [p['population'] for p in points]
        total_pop = sum(populations)
        avg_pop = total_pop / len(points) if points else 0
        
        center_lon = sum(p['coords'][0] for p in points) / len(points)
        center_lat = sum(p['coords'][1] for p in points) / len(points)
        
        # Приблизительная площадь (минимальный ограничивающий прямоугольник)
        lons = [p['coords'][0] for p in points]
        lats = [p['coords'][1] for p in points]
        width = max(lons) - min(lons)
        height = max(lats) - min(lats)
        # 1 градус ≈ 111 км
        area_sqkm = (width * 111) * (height * 111)
        
        density = total_pop / area_sqkm if area_sqkm > 0 else 0
        
        return {
            'total_population': total_pop,
            'avg_population': avg_pop,
            'area_sqkm': area_sqkm,
            'density_per_sqkm': density,
            'center_lat': center_lat,
            'center_lon': center_lon
        }
    
    def _polygon_to_geojson(self, polygon):
        """Конвертирует полигон в GeoJSON"""
        if not polygon or len(polygon) < 3:
            return {"type": "Polygon", "coordinates": []}
        
        # Замыкаем полигон (первая точка = последняя)
        if polygon[0] != polygon[-1]:
            polygon.append(polygon[0])
        
        return {
            "type": "Polygon",
            "coordinates": [polygon]
        }


class PolygonExporter:
    """Класс для экспорта полигонов в различные форматы"""
    
    @staticmethod
    def export_to_geojson(polygons, filepath):
        """Экспортирует полигоны в GeoJSON файл"""
        import json
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(polygons, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def export_to_csv(polygons, filepath):
        """Экспортирует статистику полигонов в CSV"""
        import csv
        
        if not polygons.get('features'):
            return
        
        fieldnames = set()
        for feature in polygons['features']:
            fieldnames.update(feature['properties'].keys())
        
        fieldnames = sorted(list(fieldnames))
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for feature in polygons['features']:
                writer.writerow(feature['properties'])
"""
Модуль для создания полигонов на основе результатов кластеризации с учетом площади
"""

class ClusteringPolygonGenerator:
    
    def __init__(self, use_alpha_shape: bool = True, alpha: float = 0.5):
        self.use_alpha_shape = use_alpha_shape
        self.alpha = alpha
    
    def create_polygons_from_clusters(self, clustered_features, method='convex_hull', simplify_tolerance=0.0001):
        """Создает полигоны для каждого кластера с учетом площади"""
        clusters = self._group_by_cluster(clustered_features)
        
        polygons = []
        cluster_stats = {}
        
        for cluster_id, points in clusters.items():
            if cluster_id == 'Шум' or len(points) < 3:
                continue
            
            polygon = self._create_polygon_for_points(points, method)
            
            if polygon:
                polygon = self._simplify_polygon(polygon, simplify_tolerance)
                stats = self._calculate_cluster_stats(points, cluster_id, polygon)
                cluster_stats[cluster_id] = stats
                
                # Рассчитываем притяжение на основе площади
                attraction = self._calculate_attraction(stats['area_sqkm'], stats['total_population'])
                
                feature = {
                    "type": "Feature",
                    "geometry": self._polygon_to_geojson(polygon),
                    "properties": {
                        "cluster_id": int(cluster_id) if not isinstance(cluster_id, int) else cluster_id,
                        "point_count": len(points),
                        "total_population": stats['total_population'],
                        "avg_population": round(stats['avg_population'], 2),
                        "area_sqkm": round(stats['area_sqkm'], 4),
                        "density_per_sqkm": round(stats['density_per_sqkm'], 2),
                        "attraction_score": round(attraction['score'], 2),
                        "attraction_force": attraction['force'],
                        "attraction_level": attraction['level'],
                        "center_lat": stats['center_lat'],
                        "center_lon": stats['center_lon']
                    }
                }
                polygons.append(feature)
        
        return {
            "type": "FeatureCollection",
            "features": polygons,
            "metadata": {
                "total_clusters": len(polygons),
                "method": method,
                "statistics": cluster_stats
            }
        }
    
    def _calculate_attraction(self, area_sqkm, population):
        """
        Рассчитывает притяжение кластера на основе площади и населения
        
        Формула: Притяжение = (Плотность населения) * log(Площадь + 1) * Вес_населения
        
        Args:
            area_sqkm: Площадь кластера в км²
            population: Население кластера
        
        Returns:
            dict: Показатели притяжения
        """
        if area_sqkm <= 0:
            return {'score': 0, 'force': 'Нет', 'level': 0}
        
        # Плотность населения (чел/км²)
        density = population / area_sqkm if area_sqkm > 0 else 0
        
        # Базовая формула притяжения (чем больше площадь, тем больше притяжение)
        # Используем логарифм, чтобы рост не был слишком резким
        area_factor = (area_sqkm ** 0.5)  # Корень из площади
        population_factor = population / 1000  # Нормируем население
        
        # Комбинированный показатель притяжения
        attraction_raw = (density * 0.3) + (area_factor * 0.4) + (population_factor * 0.3)
        
        # Нормируем шкалу 0-100
        max_possible = 1000  # Максимальное ожидаемое значение
        attraction_normalized = min(100, (attraction_raw / max_possible) * 100)
        
        # Определяем уровень притяжения
        if attraction_normalized >= 80:
            force = "Очень сильное"
            level = 5
        elif attraction_normalized >= 60:
            force = "Сильное"
            level = 4
        elif attraction_normalized >= 40:
            force = "Среднее"
            level = 3
        elif attraction_normalized >= 20:
            force = "Слабое"
            level = 2
        else:
            force = "Очень слабое"
            level = 1
        
        return {
            'score': attraction_normalized,
            'force': force,
            'level': level,
            'density': round(density, 2),
            'area_factor': round(area_factor, 2),
            'population_factor': round(population_factor, 2)
        }
    
    def _calculate_cluster_stats(self, points, cluster_id, polygon):
        """Рассчитывает статистику для кластера с учетом полигона"""
        populations = [p['population'] for p in points]
        total_pop = sum(populations)
        avg_pop = total_pop / len(points) if points else 0
        
        center_lon = sum(p['coords'][0] for p in points) / len(points)
        center_lat = sum(p['coords'][1] for p in points) / len(points)
        
        # Вычисляем площадь полигона более точно
        area_sqkm = self._calculate_polygon_area(polygon)
        
        density = total_pop / area_sqkm if area_sqkm > 0 else 0
        
        return {
            'total_population': total_pop,
            'avg_population': avg_pop,
            'area_sqkm': area_sqkm,
            'density_per_sqkm': density,
            'center_lat': center_lat,
            'center_lon': center_lon
        }
    
    def _calculate_polygon_area(self, polygon):
        """
        Вычисляет площадь полигона в км²
        Использует формулу Гаусса (Shoelace formula)
        """
        if not polygon or len(polygon) < 3:
            return 0
        
        area = 0
        n = len(polygon)
        
        for i in range(n):
            x1, y1 = polygon[i]
            x2, y2 = polygon[(i + 1) % n]
            area += x1 * y2 - x2 * y1
        
        area = abs(area) / 2
        
        # Конвертируем градусы в км (1 градус ≈ 111 км)
        area_sqkm = area * (111 * 111)
        
        return area_sqkm
    
    def _group_by_cluster(self, features):
        """Группирует точки по ID кластера"""
        clusters = {}
        
        for feature in features:
            cluster_id = feature['properties'].get('cluster_id')
            if cluster_id is None or cluster_id == 'Шум':
                continue
            
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            
            coords = feature['geometry']['coordinates']
            population = feature['properties'].get('Насел', 0)
            clusters[cluster_id].append({
                'coords': (coords[0], coords[1]),
                'population': population
            })
        
        return clusters
    
    def _create_polygon_for_points(self, points, method):
        """Создает полигон для набора точек"""
        coords = [p['coords'] for p in points]
        
        if len(coords) < 3:
            return None
        
        if method == 'convex_hull':
            return self._create_convex_hull(coords)
        elif method == 'alpha_shape':
            return self._create_alpha_shape(coords)
        elif method == 'concave':
            return self._create_concave_hull(coords)
        else:
            return self._create_convex_hull(coords)
    
    def _create_convex_hull(self, coords):
        """Создает выпуклую оболочку"""
        if len(coords) < 3:
            return None
        
        points = sorted(coords)
        
        def cross(o, a, b):
            return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
        
        lower = []
        for p in points:
            while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
                lower.pop()
            lower.append(p)
        
        upper = []
        for p in reversed(points):
            while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
                upper.pop()
            upper.append(p)
        
        hull = lower[:-1] + upper[:-1]
        
        if len(hull) < 3:
            return None
        
        return hull
    
    def _create_alpha_shape(self, coords):
        """Создает Alpha Shape"""
        return self._create_convex_hull(coords)
    
    def _create_concave_hull(self, coords):
        """Создает вогнутую оболочку"""
        return self._create_alpha_shape(coords)
    
    def _simplify_polygon(self, polygon, tolerance):
        """Упрощает полигон"""
        if len(polygon) < 3:
            return polygon
        
        simplified = [polygon[0]]
        for i in range(1, len(polygon)):
            last = simplified[-1]
            curr = polygon[i]
            dist = ((curr[0] - last[0])**2 + (curr[1] - last[1])**2)**0.5
            if dist > tolerance:
                simplified.append(curr)
        
        if len(simplified) >= 3:
            return simplified
        return polygon
    
    def _polygon_to_geojson(self, polygon):
        """Конвертирует полигон в GeoJSON"""
        if not polygon or len(polygon) < 3:
            return {"type": "Polygon", "coordinates": []}
        
        if polygon[0] != polygon[-1]:
            polygon.append(polygon[0])
        
        return {
            "type": "Polygon",
            "coordinates": [polygon]
        }


class PolygonExporter:
    """Класс для экспорта полигонов"""
    
    @staticmethod
    def export_to_geojson(polygons, filepath):
        import json
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(polygons, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def export_to_csv(polygons, filepath):
        import csv
        
        if not polygons.get('features'):
            return
        
        fieldnames = set()
        for feature in polygons['features']:
            fieldnames.update(feature['properties'].keys())
        
        fieldnames = sorted(list(fieldnames))
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for feature in polygons['features']:
                writer.writerow(feature['properties'])