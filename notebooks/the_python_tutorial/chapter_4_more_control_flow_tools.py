import marimo

__generated_with = "0.23.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 4.1. if Statements
    """)
    return


@app.cell
def _():
    x = int(input("Please enter an integer: "))

    if x < 0:
        x = 0
        print("Negative changed to zero")
    elif x == 0:
        print("Zero")
    elif x == 1:
        print("Single")
    else:
        print("More")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 4.2. for Statements
    """)
    return


@app.cell
def _():
    # Measure some strings:
    words = ["cat", "window", "defenestrate"]
    for word in words:
        print(f"This is the word: {word}\nThis is a length: {len(word)}", end="\n\n")
    return


@app.cell
def _():
    # Create a sample collection
    users = {"Hans": "active", "Éléonore": "inactive", "景太郎": "active"}

    # zero variant:  Iterate over a copy
    for user, status in users.copy().items():
        if status == "inactive":
            del users[user]

    print(f"Zero variant:   {users}")

    import copy

    # first variant:  Iterate over a copy
    for user, status in copy.deepcopy(users).items():
        if status == "inactive":
            del users[user]

    print(f"First variant:  {users}")

    # second variant:  Create a new collection
    active_users = {}
    for user, status in users.items():
        if status == "active":
            active_users[user] = status

    print(f"Second variant: {active_users}")
    return


@app.cell
def _():
    def _():
        import copy
        import time

        # 1. Подготовка данных (100_000 записей)
        large_users = {
            f"user_{i}": ("active" if i % 2 == 0 else "inactive")
            for i in range(100_000)
        }

        # --- Тест Zero варианта (.copy) ---
        users_zero = large_users.copy()

        s_perf_zero = time.perf_counter()
        s_time_zero = time.time()

        for user, status in users_zero.copy().items():
            if status == "inactive":
                del users_zero[user]

        e_time_zero = time.time()
        e_perf_zero = time.perf_counter()

        diff_perf_zero = e_perf_zero - s_perf_zero
        diff_time_zero = e_time_zero - s_time_zero

        print("=== [ZERO VARIANT: .copy()] ===")
        print(f"Modern (perf_counter): {diff_perf_zero:.5f} сек")
        print(f"Legacy (time.time):    {diff_time_zero:.5f} сек")
        print(f"Start (perf): {s_perf_zero} | Start (time): {s_time_zero}")

        # --- Тест First варианта (deepcopy) ---
        users_first = large_users.copy()

        s_perf_first = time.perf_counter()
        s_time_first = time.time()

        for user, status in copy.deepcopy(users_first).items():
            if status == "inactive":
                del users_first[user]

        e_time_first = time.time()
        e_perf_first = time.perf_counter()

        diff_perf_first = e_perf_first - s_perf_first
        diff_time_first = e_time_first - s_time_first

        print("\n=== [FIRST VARIANT: deepcopy()] ===")
        print(f"Modern (perf_counter): {diff_perf_first:.5f} сек")
        print(f"Legacy (time.time):    {diff_time_first:.5f} сек")
        print(f"Start (perf): {s_perf_first} | Start (time): {s_time_first}")

        # Финальное сравнение (используем только Modern таймер для точности)
        speedup = diff_perf_first / diff_perf_zero
        print(f"\nИТОГ: .copy() быстрее чем deepcopy() в {speedup:.1f} раз!")

    _()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Difference between .copy() and .deepcopy()

    ### 1. Mechanism: Shallow vs. Deep
    The fundamental difference lies in how "deep" Python goes when duplicating the data structure:

    * **`.copy()` (Shallow Copy):** Creates a new container object, but does **not** copy the objects inside. It merely copies the **references** (pointers) to the original items.
    * **`copy.deepcopy()` (Deep Copy):** Creates a new container and then **recursively** creates copies of every object found within. If your dictionary contains nested lists or other dictionaries, they are fully duplicated into new memory locations.



    ---

    ### 2. Performance Analysis
    The benchmarks conducted in your `marimo` notebook clearly demonstrate the "tax" paid for deep copying:

    * **Speed:** The `.copy()` method is significantly faster (approx. **4.1x** in current tests). It performs a linear $O(n)$ copy of references in highly optimized C code.
    * **Overhead:** `copy.deepcopy()` is slower because it must recursively traverse the entire structure, check for object types, and handle potential circular references, which creates massive CPU overhead.

    ---

    ### 3. Comparison & Strategy Selection

    | Feature | `.copy()` | `copy.deepcopy()` |
    | :--- | :--- | :--- |
    | **Complexity** | Low ($O(n)$) | High (Recursive traversal) |
    | **Data Integrity** | Nested objects are shared | Complete independence |
    | **RAM Usage** | Efficient | Expensive |
    | **Best Use Case** | Flat dictionaries or simple filtering to avoid `RuntimeError`. | Complex, nested JSON configs where you must ensure the original remains untouched. |

    ---

    ### 4. Tech Interview Highlights

    When explaining this to a Senior Engineer or during an interview at companies like **Google** or **Meta**, emphasize these points:

    * **Immutability:** In Data Engineering, creating a new collection is preferred over "in-place" modification. It follows functional programming principles and makes debugging easier.
    * **Profiling:** Always use `time.perf_counter()` for benchmarking. It is a **monotonic clock** with higher resolution that is unaffected by system-wide time updates.
    * **Memory Efficiency:** Using `deepcopy()` on massive datasets (millions of rows) is often considered an **anti-pattern**. It can easily lead to a `MemoryError`. For high-scale DE pipelines, favor shallow copies or **dictionary comprehensions**.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 4.3. The range() Function
    """)
    return


@app.cell
def _():
    for i in range(5):
        print(i)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Let's practice
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ###
    a simple 2D table
    """)
    return


@app.cell
def _():
    def _():
        for i in range(5):
            print(f"\n{i}", end="")
            for n in range(5):
                print(n, end="")

    _()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## [range(start, stop, step)](<https://docs.python.org/3/library/stdtypes.html#range>)

    ### In DE typically used for iterationg over a huge number of rows, preventiong **`OutOfMemory`** errors.
    """)
    return


@app.cell
def _():
    total_rows = 1_000_000
    batch_size = 50_000

    for start_idx in range(0, total_rows, batch_size):
        end_idx = start_idx + batch_size
        print(f"Processing chunk from {start_idx} to {end_idx}...")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    > ### Note: range() uses **Lazy Evaluations**
    > Using only 48 bytes of memory for start, stop и step variables
    """)
    return


@app.cell
def _():
    import sys

    small_range = range(100)
    huge_range = range(1_000_000_000)

    print(f"range(100) size:               {sys.getsizeof(small_range)} bytes")
    print(f"range(1_000_000_000_000) size: {sys.getsizeof(huge_range)} bytes")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Negative Step
    """)
    return


@app.cell
def _():
    def _():
        for i in range(10, 0, -1):
            print(f"Countdown: {i}")

    _()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### C-Style Loop vs. Python range()

    $$for (int\ i = start;\ i < stop;\ i += step)$$
    $$range(start,\ stop,\ step)$$
    """)
    return


@app.cell
def _():
    list(range(5, 10))
    return


@app.cell
def _():
    list(range(0, 10, 3))
    return


@app.cell
def _():
    list(range(-10, -100, -30))
    return


@app.cell
def _():
    def _():
        a = ["Mary", "had", "a", "little", "lamb"]
        for i in range(len(a)):
            print(i, a[i])

    _()
    return


@app.cell
def _():
    range(10)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Iterables and the sum() Function

    ### Definition
    An **Iterable** is any Python object capable of returning its members one at a time, permitting it to be iterated over in a `for` loop. Technically, an object is an iterable if it implements the `__iter__` method (which returns an iterator) or the `__getitem__` method.

    Common examples include:
    * **Sequences:** `list`, `tuple`, `str`, `range`.
    * **Collections:** `dict`, `set`.
    * **Streams:** Open file objects, generators.

    ---
    """)
    return


@app.cell
def _():
    # 1. Summing a standard list
    data_points = [10.5, 20.0, 5.25, 14.25]
    total_list = sum(data_points)

    # 2. Summing a lazy range (Memory Efficient)
    # Calculates the sum of numbers from 0 to 999,999
    total_range = sum(range(1_000_000))

    # 3. Using a generator expression (Advanced DE pattern)
    # Summing only squares of even numbers
    total_squares = sum(x**2 for x in range(10) if x % 2 == 0)

    print(f"Total from list:    {total_list}")
    print(f"Total from range:   {total_range}")
    print(f"Total from squares: {total_squares}")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Exact Distinct Counting: len(set()) vs. sum()

    ### The Logic of Uniqueness
    In Data Engineering, counting unique elements (Distinct Count) is a fundamental operation for calculating metrics like **DAU (Daily Active Users)** or **Unique IPs**.

    * **`set(data)`**: Deduplicates the input collection using a hash table. Time complexity: $O(n)$.
    * **`len()`**: Returns the number of elements in the set. Time complexity: $O(1)$.

    ### Comparison Table

    | Feature | `len(set(iterable))` | `sum(1 for _ in set(iterable))` |
    | :--- | :--- | :--- |
    | **Performance** | High (optimized C implementation) | Lower (Python loop overhead) |
    | **Readability** | Standard Pythonic way | Counter-intuitive |
    | **Memory** | Stores all unique keys in RAM | Stores all unique keys in RAM |

    ### Interview Insight: Exact vs. Approximate Counting
    At the scale of **Big Data** (e.g., billions of rows in Spark or BigQuery), keeping a `set` of all unique IDs in memory becomes impossible (**OutOfMemory**).

    1. **Exact Count:** `len(set())` is perfect for small to medium datasets that fit in a single machine's RAM.
    2. **Approximate Count (HyperLogLog):** For massive streams, DEs use algorithms like **HyperLogLog (HLL)**. It provides a count with ~1-2% error but uses only a few kilobytes of memory regardless of whether you have 1 million or 1 billion unique users.
    """)
    return


@app.cell
def _():
    import random
    import time

    # 1. Generating a large dataset (10,000,000 entries)
    # We create a list with many duplicates to simulate real user logs
    print("Generating data... Please wait.")
    large_user_log = [
        f"user_{random.randint(1, 100_000_000)}" for _ in range(10_000_000)
    ]

    # --- Method 1: Full process ---
    start_fast = time.perf_counter()
    res1 = len(set(large_user_log))
    time_fast = time.perf_counter() - start_fast

    # --- Method 2: Full process ---
    start_slow = time.perf_counter()
    res2 = sum(1 for _ in set(large_user_log))
    time_slow = time.perf_counter() - start_slow

    print("\n=== Performance Results (10M records) ===")
    print(f"Method 1 [len(set())]:      {time_fast:.5f} sec")
    print(f"Method 2 [sum(generator)]: {time_slow:.5f} sec")

    if time_fast > 0:
        print(
            f"\nSPEEDUP: len(set()) is {(time_slow / time_fast):.1f}x faster than sum()."
        )
    return


@app.cell
def _():
    for n in range(2, 10):
        for x in range(2, n):
            if n % x == 0:
                print(f"{n} equals {x} * {n // x}")
                break
    return


if __name__ == "__main__":
    app.run()
