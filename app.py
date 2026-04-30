import os
import json
from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from clustering_polygons import ClusteringPolygonGenerator, PolygonExporter
from qgis.core import (
    QgsApplication,
    QgsVectorLayer,
    QgsCoordinateTransform,
    QgsProject,
    QgsCoordinateReferenceSystem,
    QgsSettings,
    QgsGeometry
)

# ----------------------------
# Инициализация QGIS
# ----------------------------
QgsApplication.setPrefixPath(r"C:\Program Files\QGIS 3.44.3", True)
qgs = QgsApplication([], False)
qgs.initQgis()
QgsSettings().setValue("SHAPE_RESTORE_SHX", "YES")  # автосоздание .shx

# ----------------------------
# FastAPI
# ----------------------------
app = FastAPI()

# Разрешаем CORS для разработки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Монтаж статических папок
app.mount("/css", StaticFiles(directory="css"), name="css")
app.mount("/js", StaticFiles(directory="js"), name="js")


# ----------------------------
# Папка с данными
# ----------------------------
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
SHAPEFILE = os.path.join(DATA_DIR, "attract.shp")
GPX_FILE = os.path.join(DATA_DIR, "water.gpx")
PARKS_FILE = os.path.join(DATA_DIR, "parks.gpx")
GRAVE_FILE = os.path.join(DATA_DIR, "grave_yard.gpx")
POLYGONS_FILE = os.path.join(DATA_DIR, "polygons.geojson")
BUILDINGS_POP = os.path.join(DATA_DIR, "buildings_pop.shp")
# ----------------------------
# Преобразуем QVariant в Python типы
# ----------------------------
def variant_to_python(value):
    try:
        return int(value)
    except:
        try:
            return float(value)
        except:
            return str(value)

# ----------------------------
# Функция загрузки слоя и конвертации в GeoJSON
# ----------------------------
def layer_to_geojson(file_path, layer_name=None):
    if layer_name:
        layer_path = f"{file_path}|layername={layer_name}"
    else:
        layer_path = file_path

    # Загружаем слой без автоматического определения CRS
    layer = QgsVectorLayer(layer_path, "layer", "ogr")
    
    if not layer.isValid():
        return {"error": f"Layer not valid: {file_path}"}

    # 1. Жестко говорим, что исходные данные в МЕТРАХ (3857)
    
    # 2. Указываем кодировку, чтобы не было кракозябр
    layer.setProviderEncoding("CP1251") 

    # 3. Настраиваем трансформатор В ГРАДУСЫ
    target_crs = QgsCoordinateReferenceSystem("EPSG:4326")
    context = QgsProject.instance()
    
    
    transformer = QgsCoordinateTransform(layer.crs(), target_crs, context)

    features_geojson = []
    for feat in layer.getFeatures():
        geom = feat.geometry()
        if geom.isNull():
            continue
            
        # Клонируем геометрию, чтобы не испортить исходник, и трансформируем
        temp_geom = QgsGeometry(geom)
        error_code = temp_geom.transform(transformer)
        
        # Если трансформация прошла успешно
        if error_code == 0:
            geom_json = json.loads(temp_geom.asJson())
            properties = {f.name(): variant_to_python(feat[f.name()]) for f in layer.fields()}
            
            features_geojson.append({
                "type": "Feature",
                "geometry": geom_json,
                "properties": properties
            })

    return {"type": "FeatureCollection", "features": features_geojson}
@app.get("/load-buildings-pop")
def load_buildings_pop():
    if not os.path.exists(BUILDINGS_POP):
        return {"error": "Buildings file not found"}
    # Используем функцию конвертации
    return JSONResponse(content=layer_to_geojson(BUILDINGS_POP))
# ----------------------------
# Endpoint для shapefile
# ----------------------------
@app.get("/load-shapefile")
def load_shapefile():
    if not os.path.exists(SHAPEFILE):
        return {"error": "Shapefile not found"}
    return JSONResponse(content=layer_to_geojson(SHAPEFILE))

# ----------------------------
# Endpoint для GPX
# ----------------------------
@app.get("/load-gpx")
def load_gpx():
    if not os.path.exists(GPX_FILE):
        return {"error": "GPX file not found"}
   
    return JSONResponse(content=layer_to_geojson(GPX_FILE, layer_name="tracks"))

@app.get("/load-parks")
def load_parks():
    if not os.path.exists(PARKS_FILE):
        return {"error": "parks.gpx not found"}

    return JSONResponse(content=layer_to_geojson(PARKS_FILE, layer_name="tracks"))

@app.get("/load-graveyard")
def load_graveyard():
    if not os.path.exists(GRAVE_FILE):
        return {"error": "grave_yard.gpx not found"}

    return JSONResponse(content=layer_to_geojson(GRAVE_FILE, layer_name="tracks"))

@app.get("/load-polygons")
def load_polygons():

    if not os.path.exists(POLYGONS_FILE):
        return {"error": "polygons.geojson not found"}

    with open(POLYGONS_FILE, encoding="utf-8") as f:
        data = json.load(f)

    return JSONResponse(content=data)
# ----------------------------
# Эндпоинты для работы с полигонами кластеров
# ----------------------------

@app.post("/generate-cluster-polygons")
async def generate_cluster_polygons(request: dict):
    """
    Генерирует полигоны на основе кластеризованных данных
    Ожидает: {"clustered_features": [...], "method": "convex_hull"}
    """
    try:
        clustered_features = request.get('clustered_features', [])
        method = request.get('method', 'convex_hull')
        use_alpha = request.get('use_alpha_shape', False)
        alpha = request.get('alpha', 0.5)
        
        if not clustered_features:
            return JSONResponse(
                status_code=400,
                content={"error": "No clustered features provided"}
            )
        
        # Создаем генератор полигонов
        generator = ClusteringPolygonGenerator(
            use_alpha_shape=use_alpha,
            alpha=alpha
        )
        
        # Генерируем полигоны
        polygons = generator.create_polygons_from_clusters(
            clustered_features=clustered_features,
            method=method,
            simplify_tolerance=0.0001
        )
        
        return JSONResponse(content=polygons)
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error generating polygons: {str(e)}"}
        )


@app.post("/export-polygons")
async def export_polygons(request: dict):
    """
    Экспортирует полигоны в файл
    Ожидает: {"polygons": {...}, "format": "geojson", "filename": "output.geojson"}
    """
    try:
        polygons = request.get('polygons')
        format_type = request.get('format', 'geojson')
        filename = request.get('filename', f'clusters.{format_type}')
        
        if not polygons:
            return JSONResponse(
                status_code=400,
                content={"error": "No polygons provided"}
            )
        
        # Сохраняем в папку exports
        export_dir = os.path.join(BASE_DIR, "exports")
        os.makedirs(export_dir, exist_ok=True)
        
        filepath = os.path.join(export_dir, filename)
        
        if format_type == 'geojson':
            PolygonExporter.export_to_geojson(polygons, filepath)
        elif format_type == 'shapefile':
            shapefile_path = filepath.replace('.shp', '') + '.shp'
            success = PolygonExporter.export_to_shapefile(polygons, shapefile_path)
            if not success:
                return JSONResponse(
                    status_code=500,
                    content={"error": "Failed to export to shapefile. Install geopandas: pip install geopandas"}
                )
        elif format_type == 'csv':
            PolygonExporter.export_to_csv(polygons, filepath)
        else:
            return JSONResponse(
                status_code=400,
                content={"error": f"Unsupported format: {format_type}"}
            )
        
        return JSONResponse(content={
            "message": f"Exported successfully",
            "filepath": filepath,
            "format": format_type
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error exporting: {str(e)}"}
        )
    
# Открывает основную страницу
@app.get("/")
async def root():
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())