import time

def func(n):
    for i in range(n):
        time.sleep(2)
        print(f"hi {i}")

func()