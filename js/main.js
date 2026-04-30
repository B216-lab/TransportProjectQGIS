// Точка входа приложения
document.addEventListener('DOMContentLoaded', () => {
    // Инициализация компонентов карты
    initDrawnItems();
    createDrawControl();
    
    // Инициализация UI обработчиков
    initUIEventListeners();
    
    // Загрузка начальных данных
    loadLayer('buildings');
    loadLayer('water');
    loadLayer('parks');
    loadLayer('graveyard');
    
    // Если нужно загрузить демо-данные зданий (если бэкенд не доступен)
    // layers.buildings.data = demoBuildings;
    // displayLayer('buildings');
    
    console.log('Приложение инициализировано');
});