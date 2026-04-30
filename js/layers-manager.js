// Конфигурация слоев
const layers = {
    buildings: { layer: null, data: null, visible: true, url: '/load-buildings-pop', isBarrier: false },
    water: { layer: null, data: null, visible: false, url: '/load-gpx', isBarrier: true, color: "#4fc3f7", name: "Водные пути" },
    parks: { layer: null, data: null, visible: false, url: '/load-parks', isBarrier: true, color: "#81c784", name: "Парки" },
    graveyard: { layer: null, data: null, visible: false, url: '/load-graveyard', isBarrier: true, color: "#8d6e63", name: "Кладбища" },
    attract: { layer: null, data: null, visible: false, url: '/load-shapefile', isBarrier: false },
    polygons: { layer: null, data: null, visible: false, url: '/load-polygons', isBarrier: true, color: "#ab47bc", name: "Полигоны" }
};

// Загрузка слоя
async function loadLayer(layerKey) {
    const layerConfig = layers[layerKey];
    if (!layerConfig) return;
    if (layerConfig.data) { 
        displayLayer(layerKey); 
        return; 
    }
    showLoading(layerKey, true);
    try {
        const response = await fetch(`http://127.0.0.1:8000${layerConfig.url}`);
        const data = await response.json();
        if (data.error || !data.features || data.features.length === 0) {
            showLoading(layerKey, false);
            return;
        }
        layerConfig.data = data;
        displayLayer(layerKey);
        
        if (layerConfig.isBarrier && document.querySelector(`.barrier-checkbox[data-barrier="${layerKey}"]`)?.checked) {
            updateBarriers();
        }
        showStatus(`Загружен: ${layerKey} (${data.features.length} объектов)`, "success");
    } catch (error) {
        console.warn(`Не удалось загрузить ${layerKey}`, error);
        showLoading(layerKey, false);
    }
    showLoading(layerKey, false);
}

// Отображение слоя
function displayLayer(layerKey) {
    const layerConfig = layers[layerKey];
    if (!layerConfig || !layerConfig.data) return;
    if (layerConfig.layer) map.removeLayer(layerConfig.layer);
    
    const style = getLayerStyle(layerKey);
    layerConfig.layer = L.geoJSON(layerConfig.data, {
        pointToLayer: (f, latlng) => {
            if (layerKey === 'buildings') {
                const pop = f.properties["Насел"] || 100;
                return L.circleMarker(latlng, {
                    radius: Math.min(9, Math.max(4, Math.sqrt(pop) / 5)),
                    fillColor: "#ff6b6b",
                    color: "#fff",
                    weight: 1.5,
                    fillOpacity: 0.85
                });
            }
            return L.circleMarker(latlng, { radius: 5, fillColor: style.color, color: "#fff", weight: 1, fillOpacity: 0.7 });
        },
        style: (f) => {
            if (layerKey === 'polygons' && f.geometry.type !== 'Point') {
                return { color: "#ab47bc", weight: 2, fillColor: "#ce93d8", fillOpacity: 0.4 };
            }
            return null;
        },
        onEachFeature: (f, l) => {
            let txt = `<b>${layerConfig.name || layerKey}</b><br>`;
            for (const [k,v] of Object.entries(f.properties || {})) txt += `${k}: ${v}<br>`;
            l.bindPopup(txt);
        }
    });
    if (layerConfig.visible) layerConfig.layer.addTo(map);
}

// Получение стиля слоя
function getLayerStyle(layerKey) {
    const styles = {
        water: { color: "#4fc3f7" },
        parks: { color: "#81c784" },
        graveyard: { color: "#8d6e63" },
        attract: { color: "#ffb74d" },
        polygons: { color: "#ab47bc" }
    };
    return styles[layerKey] || { color: "#ccc" };
}

// Переключение видимости слоя
function toggleLayer(layerKey, visible) {
    const cfg = layers[layerKey];
    if (!cfg) return;
    cfg.visible = visible;
    if (cfg.layer) visible ? cfg.layer.addTo(map) : map.removeLayer(cfg.layer);
    else if (visible) loadLayer(layerKey);
}

// Показать индикатор загрузки
function showLoading(layerKey, show) {
    const cb = document.querySelector(`.layer-checkbox[data-layer="${layerKey}"]`);
    if (!cb) return;
    const parent = cb.closest('.layerItem');
    if (parent) {
        let loader = parent.querySelector('.loader');
        if (show && !loader) { 
            loader = document.createElement('span'); 
            loader.className = 'loader'; 
            parent.appendChild(loader); 
        }
        else if (!show && loader) loader.remove();
    }
}