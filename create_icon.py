from PIL import Image, ImageDraw
import math

def draw_icon(size):
    """Рисует белую звезду на красном фоне."""
    # Создаем RGB изображение с красным фоном
    img = Image.new("RGB", (size, size), (220, 20, 60))  # Crimson - красный фон
    draw = ImageDraw.Draw(img)
    
    # Центр изображения
    center_x = size // 2
    center_y = size // 2
    
    # Радиусы для звезды (внешний и внутренний)
    padding = int(size * 0.15)
    outer_radius = (size - padding * 2) // 2
    inner_radius = outer_radius * 0.4  # Внутренний радиус для остроконечной звезды
    
    # Количество вершин звезды (5 для классической звезды)
    num_points = 5
    
    # Вычисляем координаты вершин звезды
    points = []
    for i in range(num_points * 2):
        angle = math.pi / 2 - (i * math.pi / num_points)  # Начинаем сверху
        if i % 2 == 0:
            # Внешние вершины
            radius = outer_radius
        else:
            # Внутренние вершины
            radius = inner_radius
        
        x = center_x + radius * math.cos(angle)
        y = center_y - radius * math.sin(angle)
        points.append((x, y))
    
    # Рисуем белую звезду
    white_color = (255, 255, 255)
    draw.polygon(points, fill=white_color)
    
    return img

# Размеры иконки
sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
icons = [draw_icon(s) for s, _ in sizes]

# Изображения уже в RGB режиме, просто убеждаемся
rgb_icons = []
for icon in icons:
    # Убеждаемся, что изображение в RGB режиме (не палитра)
    if icon.mode != "RGB":
        rgb_img = icon.convert("RGB")
    else:
        rgb_img = icon
    rgb_icons.append(rgb_img)

# Сохранение с явным указанием формата и цветов
# ВАЖНО: Изображения уже в RGB режиме с красным фоном, что гарантирует
# сохранение цветов и избегает автоматической конвертации в градации серого
try:
    rgb_icons[0].save(
        "app.ico",
        format="ICO",
        sizes=sizes,
        append_images=rgb_icons[1:]
    )
    print("[OK] Иконка 'app.ico' создана!")
    print("   Дизайн: белая звезда на красном фоне")
    print("   Цвета: красный фон (Crimson), белая звезда")
except Exception as e:
    print(f"[ОШИБКА] Ошибка при сохранении: {e}")
    # Альтернативный способ - сохранить каждое изображение отдельно
    print("Попытка альтернативного метода сохранения...")
    rgb_icons[0].save("app.ico", format="ICO")
    print("[OK] Иконка 'app.ico' создана (только один размер)")