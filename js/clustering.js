// K-means кластеризация с учетом барьеров
function kMeansWithBarriers(points, k) {
    const groups = groupPointsByBarriers(points);
    const allLabels = new Array(points.length).fill(-1);
    let globalClusterOffset = 0;
    
    for (const [groupKey, groupPoints] of groups.entries()) {
        if (groupPoints.length === 0) continue;
        
        const nClusters = Math.min(k, Math.max(1, Math.floor(groupPoints.length / 5)));
        if (nClusters <= 1 || groupPoints.length < nClusters) {
            for (let i = 0; i < groupPoints.length; i++) {
                const originalIdx = points.indexOf(groupPoints[i]);
                allLabels[originalIdx] = globalClusterOffset;
            }
            globalClusterOffset += 1;
            continue;
        }
        
        const coords = groupPoints.map(p => [p.lng, p.lat]);
        const labels = kMeansClustering(coords, nClusters);
        
        for (let i = 0; i < groupPoints.length; i++) {
            const originalIdx = points.indexOf(groupPoints[i]);
            allLabels[originalIdx] = globalClusterOffset + labels[i];
        }
        globalClusterOffset += nClusters;
    }
    
    return allLabels;
}

// K-means алгоритм
function kMeansClustering(coords, k) {
    if (coords.length < k) k = coords.length;
    if (k === 0) return new Array(coords.length).fill(0);
    
    let centroids = [];
    for (let i = 0; i < k; i++) centroids.push([coords[i % coords.length][0], coords[i % coords.length][1]]);
    let labels = new Array(coords.length).fill(0);
    let changed = true, iter = 0;
    
    while (changed && iter < 100) {
        changed = false;
        for (let i = 0; i < coords.length; i++) {
            let best = 0, bestDist = Infinity;
            for (let j = 0; j < centroids.length; j++) {
                const d = Math.hypot(coords[i][0] - centroids[j][0], coords[i][1] - centroids[j][1]);
                if (d < bestDist) { bestDist = d; best = j; }
            }
            if (labels[i] !== best) { labels[i] = best; changed = true; }
        }
        
        const newCent = Array(k).fill().map(() => [0, 0]);
        const cnt = Array(k).fill(0);
        for (let i = 0; i < coords.length; i++) {
            newCent[labels[i]][0] += coords[i][0];
            newCent[labels[i]][1] += coords[i][1];
            cnt[labels[i]]++;
        }
        for (let j = 0; j < k; j++) if (cnt[j] > 0) { newCent[j][0] /= cnt[j]; newCent[j][1] /= cnt[j]; }
        centroids = newCent;
        iter++;
    }
    return labels;
}

// DBSCAN с учетом барьеров
function dbscanWithBarriers(points, epsilon, minSamples) {
    const groups = groupPointsByBarriers(points);
    const allLabels = new Array(points.length).fill(-1);
    let globalClusterOffset = 0;
    
    for (const [groupKey, groupPoints] of groups.entries()) {
        if (groupPoints.length < minSamples) {
            for (let i = 0; i < groupPoints.length; i++) {
                const originalIdx = points.indexOf(groupPoints[i]);
                allLabels[originalIdx] = -1;
            }
            continue;
        }
        
        const coords = groupPoints.map(p => [p.lng, p.lat]);
        const labels = dbscanClustering(coords, epsilon, minSamples);
        
        let maxLocalLabel = -1;
        for (const label of labels) {
            if (label > maxLocalLabel) maxLocalLabel = label;
        }
        
        for (let i = 0; i < groupPoints.length; i++) {
            const originalIdx = points.indexOf(groupPoints[i]);
            if (labels[i] === -1) {
                allLabels[originalIdx] = -1;
            } else {
                allLabels[originalIdx] = globalClusterOffset + labels[i];
            }
        }
        if (maxLocalLabel > -1) {
            globalClusterOffset += (maxLocalLabel + 1);
        }
    }
    
    const uniqueClusters = [...new Set(allLabels.filter(l => l !== -1))];
    const clusterMap = new Map();
    uniqueClusters.forEach((oldId, idx) => clusterMap.set(oldId, idx));
    
    for (let i = 0; i < allLabels.length; i++) {
        if (allLabels[i] !== -1) {
            allLabels[i] = clusterMap.get(allLabels[i]);
        }
    }
    
    return allLabels;
}

// DBSCAN алгоритм (исправленный)
function dbscanClustering(coords, epsilon, minSamples) {
    const n = coords.length;
    const labels = new Array(n).fill(-1);
    let clusterId = 0;
    
    for (let i = 0; i < n; i++) {
        if (labels[i] !== -1) continue;
        
        // Находим всех соседей для точки i
        const neighbors = [];
        for (let j = 0; j < n; j++) {
            const dist = Math.hypot(coords[i][0] - coords[j][0], coords[i][1] - coords[j][1]);
            const distMeters = dist * 111000;
            if (distMeters <= epsilon) {
                neighbors.push(j);
            }
        }
        
        // Если недостаточно соседей - шум
        if (neighbors.length < minSamples) {
            labels[i] = -1;
            continue;
        }
        
        // Начинаем новый кластер
        labels[i] = clusterId;
        
        // Очередь для расширения кластера
        const queue = [...neighbors];
        
        while (queue.length > 0) {
            const current = queue.shift();
            
            // Если точка уже отмечена как шум, переключаем в кластер
            if (labels[current] === -1) {
                labels[current] = clusterId;
            }
            
            // Если точка уже принадлежит текущему кластеру, пропускаем
            if (labels[current] !== undefined && labels[current] !== clusterId) {
                continue;
            }
            
            // Маркируем точку
            labels[current] = clusterId;
            
            // Находим соседей для текущей точки
            const currentNeighbors = [];
            for (let j = 0; j < n; j++) {
                const dist = Math.hypot(coords[current][0] - coords[j][0], coords[current][1] - coords[j][1]);
                const distMeters = dist * 111000;
                if (distMeters <= epsilon) {
                    currentNeighbors.push(j);
                }
            }
            
            // Если достаточно соседей, добавляем их в очередь
            if (currentNeighbors.length >= minSamples) {
                for (const nb of currentNeighbors) {
                    if (labels[nb] !== clusterId && labels[nb] !== -2) {
                        if (!queue.includes(nb)) {
                            queue.push(nb);
                        }
                    }
                }
            }
        }
        
        clusterId++;
    }
    
    return labels;
}

// Получение точек в выбранной области
function getPointsInArea() {
    if (!layers.buildings.data || !selectedArea) return [];
    return layers.buildings.data.features.filter(f => {
        const [lng, lat] = f.geometry.coordinates;
        const pt = L.latLng(lat, lng);
        if (selectedArea instanceof L.Rectangle) return selectedArea.getBounds().contains(pt);
        if (selectedArea instanceof L.Circle) return map.distance(pt, selectedArea.getLatLng()) <= selectedArea.getRadius();
        return false;
    });
}

// Выполнение кластеризации
async function performClustering() {
    if (!layers.buildings.data || layers.buildings.data.features.length === 0) {
        showStatus("Нет данных о зданиях", "error");
        return;
    }
    
    let targetFeatures = layers.buildings.data.features;
    if (selectedArea) {
        targetFeatures = getPointsInArea();
        if (targetFeatures.length === 0) {
            showStatus("В выбранной области нет зданий", "error");
            return;
        }
    }
    
    updateBarriers();
    
    showStatus(`Обработка ${targetFeatures.length} зданий с учетом ${barrierGeometries.length} барьеров...`, "info");
    
    const points = targetFeatures.map(f => ({
        lat: f.geometry.coordinates[1],
        lng: f.geometry.coordinates[0],
        feature: f
    }));
    
    let labels = [];
    const method = document.getElementById('clusteringMethod').value;
    
    if (method === 'kmeans') {
        const k = parseInt(document.getElementById('kmeansClusters').value);
        labels = kMeansWithBarriers(points, k);
    } else if (method === 'dbscan') {
        const epsilon = parseFloat(document.getElementById('dbscanEpsilon').value);
        const minSamples = parseInt(document.getElementById('dbscanMinSamples').value);
        labels = dbscanWithBarriers(points, epsilon, minSamples);
    }
    
    displayClusteringResults(targetFeatures, labels, method);
}

// Отображение результатов кластеризации
// Отображение результатов кластеризации
function displayClusteringResults(features, labels, method) {
    if (clusteringResultLayer) map.removeLayer(clusteringResultLayer);
    
    // Генерируем цвета динамически на основе уникальных кластеров
    const uniqueClusters = [...new Set(labels.filter(l => l !== -1))];
    const colorMap = new Map();
    uniqueClusters.forEach((clusterId, idx) => {
        // Используем золотое сечение для равномерного распределения цветов
        const hue = (idx * 137.5) % 360;
        colorMap.set(clusterId, `hsl(${hue}, 70%, 55%)`);
    });
    
    const featuresWithClusters = features.map((f, i) => ({
        type: "Feature",
        geometry: f.geometry,
        properties: {
            ...f.properties,
            cluster_id: labels[i] === -1 ? 'Шум' : labels[i],
            method: method
        }
    }));
    
    clusteringResultLayer = L.geoJSON({ type: "FeatureCollection", features: featuresWithClusters }, {
        pointToLayer: (f, latlng) => {
            const cid = f.properties.cluster_id;
            let col;
            if (cid === 'Шум') {
                col = '#95a5a6'; // серый для шума
            } else {
                col = colorMap.get(parseInt(cid));
            }
            const pop = f.properties["Насел"] || 100;
            return L.circleMarker(latlng, {
                radius: Math.min(8, Math.max(4, Math.sqrt(pop) / 5)),
                fillColor: col,
                color: '#fff',
                weight: 2,
                fillOpacity: 0.85
            });
        },
        onEachFeature: (f, layer) => {
            layer.bindPopup(`
                <b>Население:</b> ${f.properties["Насел"]}<br>
                <b>Кластер:</b> ${f.properties.cluster_id}<br>
                <b>Метод:</b> ${f.properties.method}<br>
                <b>Барьеров учтено:</b> ${barrierGeometries.length}
            `);
        }
    });
    
    clusteringResultLayer.addTo(map);
    
    showStatus(`Районирование выполнено: ${uniqueClusters.length} кластеров, учтено ${barrierGeometries.length} барьеров`, "success");
}

// Очистка результатов кластеризации
function clearClustering() {
    if (clusteringResultLayer) map.removeLayer(clusteringResultLayer);
    if (polygonLayer) map.removeLayer(polygonLayer);
    currentPolygons = null;
    showStatus("Результаты районирования очищены", "info");
}