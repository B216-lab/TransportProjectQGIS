// Показ статуса
function showStatus(msg, type) {
    const div = document.createElement('div');
    div.className = `status ${type}`;
    div.textContent = msg;
    div.style.cssText = 'position:fixed; bottom:20px; right:360px; z-index:2000; padding:10px 15px; border-radius:6px; max-width:350px; box-shadow:0 2px 8px rgba(0,0,0,0.2); background:white; font-weight:500;';
    document.body.appendChild(div);
    setTimeout(() => div.remove(), 4000);
}

// Переключение группы слоев
function toggleGroup(header) {
    const content = header.nextElementSibling;
    const icon = header.querySelector('.toggle-icon');
    if (content.classList.contains('collapsed')) {
        content.classList.remove('collapsed');
        icon.textContent = '▼';
    } else {
        content.classList.add('collapsed');
        icon.textContent = '▶';
    }
}

// Инициализация слоя для рисования
function initDrawnItems() {
    if (drawnItems) map.removeLayer(drawnItems);
    drawnItems = new L.FeatureGroup();
    map.addLayer(drawnItems);
}

// Создание контрола для рисования
function createDrawControl() {
    if (drawControl) map.removeControl(drawControl);
    const opts = {
        position: 'topleft',
        draw: {
            rectangle: { shapeOptions: { color: '#ff0000', weight: 3, fillOpacity: 0.2 } },
            circle: { shapeOptions: { color: '#ff0000', weight: 3, fillOpacity: 0.2 } },
            polygon: false, polyline: false, marker: false, circlemarker: false
        },
        edit: { featureGroup: drawnItems, edit: true, remove: true }
    };
    if (currentDrawType === 'rectangle') opts.draw.circle = false;
    if (currentDrawType === 'circle') opts.draw.rectangle = false;
    drawControl = new L.Control.Draw(opts);
    map.addControl(drawControl);
    
    map.on(L.Draw.Event.CREATED, e => {
        drawnItems.clearLayers();
        const layer = e.layer;
        drawnItems.addLayer(layer);
        selectedArea = layer;
        const areaStatus = document.getElementById('areaStatus');
        areaStatus.textContent = "Область выбрана! Нажмите «Выполнить районирование»";
        areaStatus.className = "status success";
    });
    
    map.on(L.Draw.Event.DELETED, () => {
        selectedArea = null;
        const areaStatus = document.getElementById('areaStatus');
        areaStatus.textContent = "Нажмите на иконку рисования на карте";
        areaStatus.className = "status info";
    });
}

// Очистка выбранной области
function clearSelectedArea() {
    if (drawnItems) drawnItems.clearLayers();
    selectedArea = null;
    const areaStatus = document.getElementById('areaStatus');
    areaStatus.textContent = "Нажмите на иконку рисования на карте";
    areaStatus.className = "status info";
    showStatus("🗑 Область очищена", "info");
}

// Смена типа рисования
function changeDrawType(type) {
    currentDrawType = type;
    clearSelectedArea();
    createDrawControl();
    const selectRectangleBtn = document.getElementById('selectRectangleBtn');
    const selectCircleBtn = document.getElementById('selectCircleBtn');
    selectRectangleBtn.classList.toggle('active', type === 'rectangle');
    selectCircleBtn.classList.toggle('active', type === 'circle');
}

// Инициализация всех UI обработчиков
function initUIEventListeners() {
    // Чекбоксы слоев
    document.querySelectorAll('.layer-checkbox').forEach(cb => {
        cb.addEventListener('change', e => toggleLayer(e.target.dataset.layer, e.target.checked));
    });
    
    // Чекбоксы барьеров
    document.querySelectorAll('.barrier-checkbox').forEach(cb => {
        cb.addEventListener('change', () => {
            const layerKey = cb.dataset.barrier;
            if (layers[layerKey] && !layers[layerKey].data) {
                loadLayer(layerKey);
            } else {
                updateBarriers();
            }
        });
    });
    
    // Кнопки рисования
    const selectRectangleBtn = document.getElementById('selectRectangleBtn');
    const selectCircleBtn = document.getElementById('selectCircleBtn');
    const clearAreaBtn = document.getElementById('clearAreaBtn');
    const performBtn = document.getElementById('performClusteringBtn');
    const clearClusteringBtn = document.getElementById('clearClusteringBtn');
    
    selectRectangleBtn.addEventListener('click', () => changeDrawType('rectangle'));
    selectCircleBtn.addEventListener('click', () => changeDrawType('circle'));
    clearAreaBtn.addEventListener('click', clearSelectedArea);
    performBtn.addEventListener('click', performClustering);
    clearClusteringBtn.addEventListener('click', clearClustering);
    
    // Методы кластеризации
    const methodSelect = document.getElementById('clusteringMethod');
    const kmeansParams = document.getElementById('kmeansParams');
    const dbscanParams = document.getElementById('dbscanParams');
    
    methodSelect.addEventListener('change', () => {
        const m = methodSelect.value;
        kmeansParams.style.display = m === 'kmeans' ? 'block' : 'none';
        dbscanParams.style.display = m === 'dbscan' ? 'block' : 'none';
    });
    
    // Полигоны
    const polygonMethodSelect = document.getElementById('polygonMethod');
    const alphaParams = document.getElementById('alphaParams');
    const alphaValue = document.getElementById('alphaValue');
    const alphaValueDisplay = document.getElementById('alphaValueDisplay');
    const generatePolygonsBtn = document.getElementById('generatePolygonsBtn');
    const exportPolygonsBtn = document.getElementById('exportPolygonsBtn');
    const attractionDisplay = document.getElementById('attractionDisplay');
    
    polygonMethodSelect.addEventListener('change', () => {
        alphaParams.style.display = polygonMethodSelect.value === 'alpha_shape' ? 'block' : 'none';
    });
    
    alphaValue.addEventListener('input', () => {
        alphaValueDisplay.textContent = alphaValue.value;
    });
    
    generatePolygonsBtn.addEventListener('click', generatePolygons);
    exportPolygonsBtn.addEventListener('click', exportPolygons);
    attractionDisplay.addEventListener('change', () => {
        if (currentPolygons) {
            displayPolygons(currentPolygons);
        }
    });
}