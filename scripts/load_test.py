"""Small dependency-free smoke/load harness for a deployed treasury API.

Usage: BASE_URL=http://localhost:8000 python scripts/load_test.py
This is not a replacement for production capacity testing with k6/Locust/Gatling.
"""
from __future__ import annotations
import os, time, statistics
from concurrent.futures import ThreadPoolExecutor
from urllib.request import urlopen

BASE=os.getenv("BASE_URL","http://localhost:8000").rstrip("/")
PATHS=["/health","/api/v1/liquidity/global","/api/v1/risk/early-warning","/api/v1/production/readiness"]

def hit(path:str)->float:
    start=time.perf_counter()
    with urlopen(BASE+path, timeout=10) as r:
        if r.status != 200: raise RuntimeError(f"{path}: {r.status}")
        r.read()
    return (time.perf_counter()-start)*1000

if __name__=="__main__":
    timings=[]
    with ThreadPoolExecutor(max_workers=10) as pool:
        for ms in pool.map(hit, [PATHS[i%len(PATHS)] for i in range(100)]): timings.append(ms)
    timings.sort()
    p95=timings[int(len(timings)*0.95)-1]
    print({"requests":len(timings),"mean_ms":round(statistics.mean(timings),2),"p95_ms":round(p95,2),"max_ms":round(max(timings),2)})
