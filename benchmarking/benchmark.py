#!/usr/bin/env python3
"""
Минимальный бенчмаркинг для выполнения задания
Запрос: GET /users/{user_id}/loans-detailed
"""

import asyncio
import aiohttp
import time
import csv
import statistics
import matplotlib.pyplot as plt

# Конфигурация
LENDING_URL = "http://localhost:8003"
REQUESTS_COUNT = 100

async def measure_request(session, user_id, request_num):
    """Замерить время одного запроса"""
    url = f"{LENDING_URL}/users/{user_id}/loans-detailed?limit=10"
    
    start = time.perf_counter()
    try:
        async with session.get(url, timeout=30) as resp:
            elapsed = time.perf_counter() - start
            return {
                "num": request_num,
                "user_id": user_id,
                "time": elapsed,
                "success": resp.status == 200,
                "status": resp.status
            }
    except Exception as e:
        elapsed = time.perf_counter() - start
        return {
            "num": request_num,
            "user_id": user_id,
            "time": elapsed,
            "success": False,
            "error": str(e)
        }

async def run_benchmark():
    """Запустить бенчмаркинг"""
    print(f"Запуск бенчмаркинга: {REQUESTS_COUNT} запросов...")
    
    results = []
    async with aiohttp.ClientSession() as session:
        for i in range(1, REQUESTS_COUNT + 1):
            user_id = ((i - 1) % 100) + 1  # user_id от 1 до 100
            
            result = await measure_request(session, user_id, i)
            results.append(result)
            
            if i % 10 == 0:
                print(f"  Выполнено {i}/{REQUESTS_COUNT}")
    
    return results

def save_results(results, filename="benchmark_results.csv"):
    """Сохранить таблицу с выборкой в CSV"""
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Номер вызова", "user_id", "Время (сек)", "Успех"])
        
        for r in results:
            writer.writerow([r["num"], r["user_id"], f"{r['time']:.4f}", r["success"]])
    
    print(f"\nТаблица сохранена: {filename}")

def calculate_stats(results):
    """Подсчитать среднюю и дисперсию"""
    # Берем только успешные запросы
    times = [r["time"] for r in results if r["success"]]
    
    if not times:
        print("Нет успешных запросов!")
        return None
    
    mean = statistics.mean(times)
    variance = statistics.variance(times) if len(times) > 1 else 0
    
    # Сохраняем статистику в файл
    with open("statistics.txt", "w", encoding="utf-8") as f:
        f.write("Результаты бенчмаркинга\n")
        f.write("="*40 + "\n")
        f.write(f"Количество запросов: {len(results)}\n")
        f.write(f"Успешных запросов: {len(times)}\n")
        f.write(f"Неудачных запросов: {len(results) - len(times)}\n")
        f.write(f"\nСреднее время выполнения: {mean:.6f} сек\n")
        f.write(f"Дисперсия: {variance:.8f}\n")
        f.write(f"Стандартное отклонение: {variance**0.5:.6f} сек\n")
        f.write(f"Минимальное время: {min(times):.4f} сек\n")
        f.write(f"Максимальное время: {max(times):.4f} сек\n")
    
    print(f"\nСтатистика сохранена: statistics.txt")
    print(f"  Среднее: {mean:.6f} сек")
    print(f"  Дисперсия: {variance:.8f}")
    
    return {"mean": mean, "variance": variance}

def plot_results(results, filename="performance_graph.png"):
    """Построить график зависимости времени от номера вызова"""
    numbers = [r["num"] for r in results if r["success"]]
    times = [r["time"] for r in results if r["success"]]
    
    plt.figure(figsize=(12, 6))
    plt.plot(numbers, times, 'b.', markersize=4, linewidth=0.5)
    plt.xlabel('Номер вызова')
    plt.ylabel('Время выполнения (секунды)')
    plt.title('Зависимость времени выполнения от номера вызова')
    plt.grid(True, alpha=0.3)
    
    # Добавляем линию среднего
    mean = statistics.mean(times)
    plt.axhline(y=mean, color='r', linestyle='--', label=f'Среднее = {mean:.4f}с')
    plt.legend()
    
    plt.tight_layout()
    plt.savefig(filename, dpi=100)
    print(f"График сохранен: {filename}")
    
    # Показываем график
    plt.show()

async def main():
    print(f"Запрос: GET /users/{{user_id}}/loans-detailed")
    
    # Проверка доступности
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{LENDING_URL}/health", timeout=5) as resp:
                if resp.status == 200:
                    print("Сервис доступен\n")
                else:
                    print(f"Сервис вернул статус {resp.status}")
    except Exception as e:
        print(f"Ошибка: сервис недоступен - {e}")
        return
    
    # Запуск
    results = await run_benchmark()
    
    # Сохранение результатов
    save_results(results)
    
    # Статистика
    stats = calculate_stats(results)
    
    # График
    plot_results(results)

if __name__ == "__main__":
    asyncio.run(main())