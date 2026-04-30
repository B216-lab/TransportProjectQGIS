// Инициализация карты
const map = L.map('map').setView([52.286, 104.305], 13);

// Базовый слой карты
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

// Легенда
const legend = L.control({ position: 'bottomleft' });
legend.onAdd = () => {
    const div = L.DomUtil.create('div', 'info legend');
    div.style.cssText = 'background:white; padding:8px 12px; border-radius:6px; border:1px solid #ccc; font-size:12px; box-shadow:0 1px 3px rgba(0,0,0,0.1); max-width:200px;';
    div.innerHTML = `
        <b>Легенда</b><br>
        <span style="background:#ff6b6b; display:inline-block; width:12px; height:12px; border-radius:50%;"></span> Здания<br>
        <span style="background:#4fc3f7; display:inline-block; width:12px; height:12px; border-radius:50%;"></span> Водные пути (барьер)<br>
        <span style="background:#81c784; display:inline-block; width:12px; height:12px; border-radius:50%;"></span> Парки (барьер)<br>
        <span style="background:#8d6e63; display:inline-block; width:12px; height:12px; border-radius:50%;"></span> Кладбища (барьер)<br>
        <span style="background:#ab47bc; display:inline-block; width:12px; height:12px;"></span> Полигоны (барьер)<br>
        <span style="background:#ff0000; display:inline-block; width:12px; height:12px;"></span> Выделенная область<br>
        <hr style="margin:5px 0">
        <span style="background:#e74c3c; display:inline-block; width:12px; height:12px; border-radius:50%;"></span> Кластеры → разные цвета
    `;
    return div;
};
legend.addTo(map);

// Глобальные переменные
let drawnItems = null;
let drawControl = null;
let currentDrawType = 'rectangle';
let selectedArea = null;
let clusteringResultLayer = null;
let currentPolygons = null;
let polygonLayer = null;
let barrierGeometries = [];

// Функция для генерации случайного цвета
function getRandomColor() {
    const hue = Math.random() * 360;
    return `hsl(${hue}, 70%, 55%)`;
}

// Функция для генерации набора цветов
function generateClusterColors(count) {
    const colors = [];
    for (let i = 0; i < count; i++) {
        const hue = (i * 137.5) % 360;
        colors.push(`hsl(${hue}, 70%, 55%)`);
    }
    return colors;
}

// Функция для обновления цветов кластеров
function updateClusterColors(colorCount) {
    clusterColors = generateClusterColors(colorCount);
}