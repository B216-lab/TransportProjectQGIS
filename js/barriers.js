// Демо-данные зданий
const demoBuildings = { type: "FeatureCollection", features: [] };
for (let i = 0; i < 350; i++) {
    const lat = 52.24 + Math.random() * 0.14;
    const lng = 104.22 + Math.random() * 0.16;
    demoBuildings.features.push({ 
        type: "Feature", 
        geometry: { type: "Point", coordinates: [lng, lat] }, 
        properties: { "Насел": 50 + Math.floor(Math.random() * 450), id: i } 
    });
}

// Обновление барьеров
function updateBarriers() {
    barrierGeometries = [];
    const barrierLayers = ['water', 'parks', 'graveyard', 'polygons'];
    
    for (const layerKey of barrierLayers) {
        const checkbox = document.querySelector(`.barrier-checkbox[data-barrier="${layerKey}"]`);
        if (checkbox && checkbox.checked && layers[layerKey] && layers[layerKey].data) {
            const features = layers[layerKey].data.features;
            for (const feature of features) {
                if (feature.geometry) {
                    try {
                        const geom = turf.feature(feature.geometry);
                        barrierGeometries.push(geom);
                    } catch(e) {}
                }
            }
        }
    }
    
    updateBarriersList();
}

// Обновление списка активных барьеров в UI
function updateBarriersList() {
    const activeBarriers = [];
    const barrierLayers = ['water', 'parks', 'graveyard', 'polygons'];
    for (const layerKey of barrierLayers) {
        const checkbox = document.querySelector(`.barrier-checkbox[data-barrier="${layerKey}"]`);
        if (checkbox && checkbox.checked && layers[layerKey] && layers[layerKey].data) {
            activeBarriers.push(layers[layerKey].name || layerKey);
        }
    }
    
    const activeBarriersList = document.getElementById('activeBarriersList');
    if (activeBarriers.length === 0) {
        activeBarriersList.innerHTML = '<span style="color:#999;">⚠️ Нет активных барьеров</span>';
    } else {
        activeBarriersList.innerHTML = activeBarriers.map(b => `<span class="badge" style="margin:2px; display:inline-block;">🚧 ${b}</span>`).join('');
    }
}

// Нахождение барьерного полигона для точки
function findBarrierPolygonForPoint(point) {
    if (barrierGeometries.length === 0) return null;
    
    const pt = turf.point([point.lng, point.lat]);
    for (const barrier of barrierGeometries) {
        try {
            if (turf.booleanPointInPolygon(pt, barrier)) {
                return barrier;
            }
        } catch(e) {}
    }
    return null;
}

// Группировка точек по барьерным полигонам
function groupPointsByBarriers(points) {
    const groups = new Map();
    
    for (const point of points) {
        const barrier = findBarrierPolygonForPoint(point);
        const groupKey = barrier ? JSON.stringify(barrier.geometry) : "outside";
        
        if (!groups.has(groupKey)) {
            groups.set(groupKey, []);
        }
        groups.get(groupKey).push(point);
    }
    
    return groups;
}