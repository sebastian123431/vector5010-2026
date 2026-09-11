import os
import sys
import base64
import cv2
import numpy as np

# Ensure django setup
sys.path.insert(0, os.path.abspath("."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vector5010.settings")
import django
django.setup()

from vectorapp.vision import vector_vision

def create_synthetic_photo():
    # Create a 400x300 BGR synthetic image
    img = np.zeros((300, 400, 3), dtype=np.uint8)
    # Gradient background (blue sky to ground)
    for y in range(300):
        img[y, :] = (int(180 - y*0.3), int(140 - y*0.2), int(100 + y*0.2))
    
    # Draw a stylized face (circle) with eyes and mouth
    cv2.circle(img, (200, 140), 50, (180, 210, 240), -1) # skin tone
    cv2.circle(img, (185, 130), 6, (40, 30, 20), -1)      # left eye
    cv2.circle(img, (215, 130), 6, (40, 30, 20), -1)      # right eye
    cv2.ellipse(img, (200, 160), (18, 8), 0, 0, 180, (50, 50, 180), 3) # smile

    # Convert to base64
    _, buf = cv2.imencode('.jpg', img)
    b64_str = "data:image/jpeg;base64," + base64.b64encode(buf).decode('utf-8')
    return img, b64_str

def main():
    print("=== TEST 1: Analizar atributos visuales ===")
    img, b64_str = create_synthetic_photo()
    attrs = vector_vision.analyze_visual_attributes(img)
    print(f"Resolución: {attrs['width']}x{attrs['height']} px")
    print(f"Orientación: {attrs['orientacion']}")
    print(f"Luminosidad: {attrs['iluminacion']} ({attrs['brillo']})")
    print(f"Nitidez: {attrs['nitidez']}")
    print(f"Colores dominantes: {attrs['tonos']}")
    assert attrs['width'] == 400
    assert attrs['height'] == 300
    assert attrs['orientacion'] == "horizontal (formato apaisado)"

    print("\n=== TEST 2: Detección de rostros Haar Cascade ===")
    face_data = vector_vision.detect_faces(img)
    print(f"Rostros detectados: {face_data['count']}")
    print(f"Detalles rostros: {face_data['faces']}")
    print(f"Resumen rostros: {face_data['summary']}")

    print("\n=== TEST 3: Comprehensive Photo Analysis ===")
    comp = vector_vision.comprehensive_photo_analysis(b64_str)
    print(f"Success: {comp['success']}")
    print(f"Summary: {comp['summary']}")
    print("Reporte técnico:")
    print(comp['technical_report'])
    assert comp['success'] is True
    assert "Resolución" in comp['technical_report']

    print("\n=== TEST 4: Guardar foto de usuario en disco ===")
    abs_path, rel_url = vector_vision.save_user_photo(b64_str, user_name="Sebastian")
    print(f"Ruta absoluta: {abs_path}")
    print(f"URL relativa: {rel_url}")
    assert os.path.exists(abs_path)
    assert rel_url.startswith("/media/user_photos/")

    print("\n>>> TODOS LOS TESTS DE VISIÓN PASARON CON ÉXITO! <<<")

if __name__ == "__main__":
    main()
