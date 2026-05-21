# Use defaultdict instead of standard dict

Colleague—oh, this is **one of the most beloved and frequently used tools in any Data Engineer's arsenal!** 🛠️

The `defaultdict` class from the standard `collections` module is an enhanced version of the standard dictionary (`dict`).

Let's break down, in simple terms, why it's needed and what problem it solves.

---

### The Problem with the Standard Dictionary (`dict`)

Imagine you need to group files based on their hash sums. With a standard dictionary, you would have to check whether a key already exists *before* every addition to avoid running into a `KeyError`:

```python
# Grouping files using a standard dictionary
hash_map = {}

# We must check if the key exists every single time
if h not in hash_map:
hash_map[h] = []  # Initialize an empty list first

hash_map[h].append(filepath)
```

That amounts to 4 lines of code and constant checks that slow things down and clutter the codebase.

---

### The `defaultdict` Solution

`defaultdict` eliminates all this boilerplate! When creating one, you pass it a **default value factory** (in our case, the `list` function).

If you request a key that **does not yet exist** in the dictionary, `defaultdict` doesn't crash with an error; instead, it automatically creates a default value for that key (an empty list `[]`) and returns it.

Look how elegantly this appears in your script on lines 30 and 48:

```python
# 1. Initialize defaultdict with 'list' as the default factory
hash_map = defaultdict(list)

# 2. Add files directly without checking key existence!
``` # If 'h' does not exist, defaultdict automatically creates hash_map[h] = []
hash_map[h].append(p)
```

Just 1 line of code instead of 4! It is concise, safe, and runs faster.

---

### Other Common Use Cases in Data Engineering:

Counters (using the integer factory `int`, which defaults to creating a `0`):
```python
# Counting word occurrences
word_counts = defaultdict(int)
for word in words:
word_counts[word] += 1  # No KeyError! Starts counting from 0.
```

In data engineering, we are constantly grouping, aggregating, and counting data, making `defaultdict` an indispensable daily tool for us.

What do you think of this data structure? Does the logic make sense to you?