"""
Сервис для работы с ORB (Oriented FAST and Rotated BRIEF)
для распознавания изображений в AR тегах
"""
import cv2
import numpy as np
import json
from pathlib import Path
from typing import Tuple, Optional, List


def extract_orb_features(image_path: str, max_features: int = 500) -> Tuple[Optional[str], Optional[bytes]]:
    """
    Извлечение ORB признаков из изображения

    Args:
        image_path: Путь к изображению (относительный от app/static/)
        max_features: Максимальное количество ключевых точек

    Returns:
        Tuple[Optional[str], Optional[bytes]]:
            - JSON строка с ключевыми точками (координаты, размер, угол, октава)
            - Бинарные дескрипторы ORB
    """
    try:
        # Формируем полный путь к файлу
        full_path = Path("app/static") / image_path

        if not full_path.exists():
            print(f"Изображение не найдено: {full_path}")
            return None, None

        # Загружаем изображение
        image = cv2.imread(str(full_path))
        if image is None:
            print(f"Не удалось загрузить изображение: {full_path}")
            return None, None

        # Конвертируем в градации серого
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Создаем ORB детектор
        orb = cv2.ORB_create(nfeatures=max_features)

        # Находим ключевые точки и дескрипторы
        keypoints, descriptors = orb.detectAndCompute(gray, None)

        if keypoints is None or descriptors is None or len(keypoints) == 0:
            print(f"Не удалось извлечь признаки из изображения: {full_path}")
            return None, None

        # Сериализуем ключевые точки в JSON
        keypoints_data = []
        for kp in keypoints:
            keypoints_data.append({
                "x": float(kp.pt[0]),
                "y": float(kp.pt[1]),
                "size": float(kp.size),
                "angle": float(kp.angle),
                "response": float(kp.response),
                "octave": int(kp.octave),
                "class_id": int(kp.class_id)
            })

        keypoints_json = json.dumps(keypoints_data)

        # Сериализуем дескрипторы в бинарный формат
        descriptors_bytes = descriptors.tobytes()

        print(f"Извлечено {len(keypoints)} ключевых точек из {full_path}")

        return keypoints_json, descriptors_bytes

    except Exception as e:
        print(f"Ошибка извлечения ORB признаков: {e}")
        return None, None


def deserialize_orb_features(keypoints_json: str, descriptors_bytes: bytes) -> Tuple[List, np.ndarray]:
    """
    Десериализация ORB признаков из базы данных

    Args:
        keypoints_json: JSON строка с ключевыми точками
        descriptors_bytes: Бинарные дескрипторы

    Returns:
        Tuple[List, np.ndarray]: Список ключевых точек cv2.KeyPoint и массив дескрипторов
    """
    try:
        # Десериализуем ключевые точки
        keypoints_data = json.loads(keypoints_json)
        keypoints = []
        for kp_data in keypoints_data:
            kp = cv2.KeyPoint(
                x=kp_data["x"],
                y=kp_data["y"],
                size=kp_data["size"],
                angle=kp_data["angle"],
                response=kp_data["response"],
                octave=kp_data["octave"],
                class_id=kp_data["class_id"]
            )
            keypoints.append(kp)

        # Десериализуем дескрипторы
        num_features = len(keypoints)
        descriptors = np.frombuffer(descriptors_bytes, dtype=np.uint8).reshape(num_features, 32)

        return keypoints, descriptors

    except Exception as e:
        print(f"Ошибка десериализации ORB признаков: {e}")
        return [], np.array([])


def match_orb_features(
    query_image_data: bytes,
    target_keypoints_json: str,
    target_descriptors_bytes: bytes,
    min_match_count: int = 10,
    ratio_threshold: float = 0.75
) -> Tuple[bool, float, int]:
    """
    Сопоставление ORB признаков между запросом (из камеры) и целевым изображением (из БД)

    Args:
        query_image_data: Бинарные данные изображения с камеры (JPEG/PNG)
        target_keypoints_json: JSON с ключевыми точками целевого изображения
        target_descriptors_bytes: Бинарные дескрипторы целевого изображения
        min_match_count: Минимальное количество совпадений для распознавания
        ratio_threshold: Порог для теста отношений Лоу (Lowe's ratio test)

    Returns:
        Tuple[bool, float, int]:
            - Найдено ли совпадение
            - Уверенность совпадения (0-100%)
            - Количество хороших совпадений
    """
    try:
        # Декодируем изображение из бинарных данных
        nparr = np.frombuffer(query_image_data, np.uint8)
        query_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if query_image is None:
            print("Не удалось декодировать изображение запроса")
            return False, 0.0, 0

        # Конвертируем в градации серого
        query_gray = cv2.cvtColor(query_image, cv2.COLOR_BGR2GRAY)

        # Создаем ORB детектор
        orb = cv2.ORB_create(nfeatures=500)

        # Находим ключевые точки и дескрипторы в запросе
        query_kp, query_desc = orb.detectAndCompute(query_gray, None)

        if query_kp is None or query_desc is None or len(query_kp) == 0:
            print("Не удалось извлечь признаки из изображения запроса")
            return False, 0.0, 0

        # Десериализуем целевые признаки
        target_kp, target_desc = deserialize_orb_features(target_keypoints_json, target_descriptors_bytes)

        if len(target_kp) == 0 or len(target_desc) == 0:
            print("Не удалось десериализовать целевые признаки")
            return False, 0.0, 0

        # Создаем BF (Brute Force) matcher с Hamming distance (для ORB)
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)

        # Находим 2 лучших совпадения для каждого дескриптора (для теста Лоу)
        matches = bf.knnMatch(query_desc, target_desc, k=2)

        # Применяем тест отношений Лоу для фильтрации хороших совпадений
        good_matches = []
        for match_pair in matches:
            if len(match_pair) == 2:
                m, n = match_pair
                if m.distance < ratio_threshold * n.distance:
                    good_matches.append(m)

        num_good_matches = len(good_matches)
        print(f"Найдено хороших совпадений: {num_good_matches}/{len(query_kp)} (мин: {min_match_count})")

        # Проверяем, достаточно ли совпадений
        if num_good_matches >= min_match_count:
            # Вычисляем уверенность как процент от найденных ключевых точек
            confidence = min(100.0, (num_good_matches / min_match_count) * 100.0)
            return True, confidence, num_good_matches

        return False, 0.0, num_good_matches

    except Exception as e:
        print(f"Ошибка сопоставления ORB признаков: {e}")
        import traceback
        traceback.print_exc()
        return False, 0.0, 0


def extract_orb_from_image_data(image_data: bytes, max_features: int = 500) -> Tuple[Optional[str], Optional[bytes]]:
    """
    Извлечение ORB признаков из бинарных данных изображения

    Args:
        image_data: Бинарные данные изображения (JPEG/PNG)
        max_features: Максимальное количество ключевых точек

    Returns:
        Tuple[Optional[str], Optional[bytes]]:
            - JSON строка с ключевыми точками
            - Бинарные дескрипторы ORB
    """
    try:
        # Декодируем изображение
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            print("Не удалось декодировать изображение")
            return None, None

        # Конвертируем в градации серого
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Создаем ORB детектор
        orb = cv2.ORB_create(nfeatures=max_features)

        # Находим ключевые точки и дескрипторы
        keypoints, descriptors = orb.detectAndCompute(gray, None)

        if keypoints is None or descriptors is None or len(keypoints) == 0:
            print("Не удалось извлечь признаки из изображения")
            return None, None

        # Сериализуем ключевые точки
        keypoints_data = []
        for kp in keypoints:
            keypoints_data.append({
                "x": float(kp.pt[0]),
                "y": float(kp.pt[1]),
                "size": float(kp.size),
                "angle": float(kp.angle),
                "response": float(kp.response),
                "octave": int(kp.octave),
                "class_id": int(kp.class_id)
            })

        keypoints_json = json.dumps(keypoints_data)
        descriptors_bytes = descriptors.tobytes()

        return keypoints_json, descriptors_bytes

    except Exception as e:
        print(f"Ошибка извлечения ORB признаков: {e}")
        return None, None
