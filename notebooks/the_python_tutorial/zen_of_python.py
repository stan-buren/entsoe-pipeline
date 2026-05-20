# Copyright 2026 Stanislav Burundukov
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import marimo

__generated_with = "0.23.5"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _():
    import keyword

    for i in keyword.kwlist:
        print(i)
    return


@app.cell
def _():

    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #The First Zen of Python: Beautiful is better than ugly.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ##The "Ugly" Implementation (Imperative)

    This approach is technically correct but "ugly" because it focuses on the mechanics (how to loop, how to index, how to manage the list) rather than the logic.
    """)
    return


@app.cell
def _():
    # Task: Get the squares of all even numbers from a list
    u_data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    u_result = []

    for i in range(len(u_data)):
        if u_data[i] % 2 == 0:
            square = u_data[i] * u_data[i]
            u_result.append(square)

    print(u_result)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ##Why this is considered "Ugly":
    * Manual Indexing: Using `range(len(data))` is an anti-pattern in Python. It adds noise and provides more opportunities for "off-by-one" errors.

    * State Management: You are forced to track the result list and the square variable manually.

    * High Boilerplate: 50% of the code is dedicated to the structure of the loop rather than the data transformation.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #The "Beautiful" Implementation (Declarative)
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ##This version uses a List Comprehension. It is "beautiful" because it expresses the "What" rather than the "How."
    """)
    return


@app.cell
def _():
    b_data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    # Beautiful: The logic is contained in a single, readable line
    squares_of_evens = [x**2 for x in b_data if x % 2 == 0]

    print(squares_of_evens)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ##Why this is "Beautiful":
    * Readability: It reads like a sentence in English: "Give me $x^2$ for every $x$ in data if $x$ is even.
    * "Immutability: You aren't "building" a list step-by-step; you are defining what the final result should look like.
    * Performance: Under the hood, Python optimizes list comprehensions to run at near-C speeds, making it more efficient than a manual .append() loop.
    """)
    return


if __name__ == "__main__":
    app.run()
