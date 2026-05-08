import asyncio
import aiohttp
import time
import csv
import statistics
import matplotlib.pyplot as plt

URL = "http://localhost:8003"
REQUESTS = 100

async def run():
    results = []
    async with aiohttp.ClientSession() as session:
        for i in range(1, REQUESTS + 1):
            user_id = ((i - 1) % 100) + 1
            start = time.perf_counter()
            
            try:
                async with session.get(f"{URL}/users/{user_id}/loans-mp", timeout=30) as resp:
                    elapsed = time.perf_counter() - start
                    results.append([i, user_id, elapsed, resp.status == 200])
            except:
                elapsed = time.perf_counter() - start
                results.append([i, user_id, elapsed, False])
            
            if i % 20 == 0:
                print(f"{i}/{REQUESTS}")
    
    return results

def save_results(results):
    with open("mp_results.csv", "w") as f:
        f.write("num,user_id,time,success\n")
        for r in results:
            f.write(f"{r[0]},{r[1]},{r[2]:.4f},{r[3]}\n")
    print("Сохранено: mp_results.csv")

def calc_stats(results):
    times = [r[2] for r in results if r[3]]
    mean = statistics.mean(times)
    var = statistics.variance(times)
    
    with open("mp_stats.txt", "w") as f:
        f.write(f"Среднее: {mean:.6f}\n")
        f.write(f"Дисперсия: {var:.8f}\n")
    
    print(f"Среднее: {mean:.6f}")
    print(f"Дисперсия: {var:.8f}")
    return times

def plot(times):
    plt.plot(range(1, len(times)+1), times, 'b.')
    plt.xlabel("Номер вызова")
    plt.ylabel("Время (сек)")
    plt.title("MessagePack: время выполнения")
    plt.savefig("mp_graph.png")
    plt.show()
    print("График: mp_graph.png")

async def main():
    print(f"MessagePack бенчмаркинг, {REQUESTS} запросов")
    results = await run()
    save_results(results)
    times = calc_stats(results)
    plot(times)

asyncio.run(main())