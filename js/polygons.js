// Генерация полигонов кластеров
async function generatePolygons() {
    if (!clusteringResultLayer) {
        showStatus("Сначала выполните районирование!", "error");
        return;
    }
    
    showStatus("Создание полигонов кластеров...", "info");
    
    const clusteredFeatures = [];
    clusteringResultLayer.eachLayer(layer => {
        if (layer.feature) {
            clusteredFeatures.push(layer.feature);
        }
    });
    
    if (clusteredFeatures.length === 0) {
        showStatus("Нет данных для создания полигонов", "error");
        return;
    }
    
    const method = document.getElementById('polygonMethod').value;
    const useAlpha = method === 'alpha_shape';
    const alpha = parseFloat(document.getElementById('alphaValue').value);
    
    try {
        const response = await fetch('http://127.0.0.1:8000/generate-cluster-polygons', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                clustered_features: clusteredFeatures,
                method: method,
                use_alpha_shape: useAlpha,
                alpha: alpha
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            showStatus(`Ошибка: ${data.error}`, "error");
            return;
        }
        
        currentPolygons = data;
        displayPolygons(data);
        showStatus(`Создано ${data.features.length} полигонов`, "success");
        
    } catch (error) {
        console.error(error);
        showStatus("Ошибка при создании полигонов", "error");
    }
}

// Отображение полигонов на карте
function displayPolygons(polygons) {
    if (polygonLayer) {
        map.removeLayer(polygonLayer);
    }
    
    const displayMode = document.getElementById('attractionDisplay').value;
    
    const attractionColors = {
        5: '#e74c3c',
        4: '#e67e22',
        3: '#f39c12',
        2: '#3498db',
        1: '#95a5a6'
    };
    
    polygonLayer = L.geoJSON(polygons, {
        style: (feature) => {
            const attractionLevel = feature.properties.attraction_level;
            const color = attractionColors[attractionLevel] || '#95a5a6';
            return {
                color: color,
                weight: 3,
                fillColor: color,
                fillOpacity: 0.3,
                opacity: 0.8
            };
        },
        onEachFeature: (feature, layer) => {
            const props = feature.properties;
            
            let attractionText = '';
            if (displayMode === 'score') {
                attractionText = `Притяжение: ${props.attraction_score}/100`;
            } else if (displayMode === 'level') {
                attractionText = `Уровень притяжения: ${props.attraction_level}/5`;
            } else if (displayMode === 'force') {
                attractionText = `Притяжение: ${props.attraction_force}`;
            }
            
            let popupContent = `
                <b>Кластер ${props.cluster_id}</b><br>
                Точек: ${props.point_count}<br>
                Население: ${props.total_population} чел.<br>
                Площадь: ${props.area_sqkm} км²<br>
                Плотность: ${props.density_per_sqkm} чел/км²<br>
                ${attractionText ? attractionText + '<br>' : ''}
                Центр: ${props.center_lat.toFixed(4)}, ${props.center_lon.toFixed(4)}
            `;
            layer.bindPopup(popupContent);
        }
    });
    
    polygonLayer.addTo(map);
    
    const attractionLegend = document.getElementById('attractionLegend');
    attractionLegend.style.display = displayMode !== 'none' ? 'block' : 'none';
}

// Экспорт полигонов
async function exportPolygons() {
    if (!currentPolygons || currentPolygons.features.length === 0) {
        showStatus("Нет полигонов для экспорта", "error");
        return;
    }
    
    const format = document.getElementById('exportFormat').value;
    const timestamp = new Date().toISOString().slice(0,19).replace(/:/g, '-');
    const filename = `clusters_${timestamp}.${format === 'shapefile' ? 'shp' : format}`;
    
    showStatus(`Экспорт в ${format}...`, "info");
    
    try {
        const response = await fetch('http://127.0.0.1:8000/export-polygons', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                polygons: currentPolygons,
                format: format,
                filename: filename
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            showStatus(`Ошибка экспорта: ${data.error}`, "error");
        } else {
            showStatus(`Экспорт завершен! Файл сохранен в папке exports`, "success");
        }
        
    } catch (error) {
        console.error(error);
        showStatus("Ошибка при экспорте", "error");
    }
}