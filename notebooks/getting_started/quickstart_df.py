import marimo

__generated_with = "0.23.0"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Quickstart: DataFrame

    This is a short introduction and quickstart for the PySpark DataFrame API. PySpark DataFrames are lazily evaluated. They are implemented on top of [RDD](https://spark.apache.org/docs/latest/rdd-programming-guide.html#overview)s. When Spark [transforms](https://spark.apache.org/docs/latest/rdd-programming-guide.html#transformations) data, it does not immediately compute the transformation but plans how to compute later. When [actions](https://spark.apache.org/docs/latest/rdd-programming-guide.html#actions) such as `collect()` are explicitly called, the computation starts.
    This notebook shows the basic usages of the DataFrame, geared mainly for new users. You can run the latest version of these examples by yourself in 'Live Notebook: DataFrame' at [the quickstart page](https://spark.apache.org/docs/latest/api/python/getting_started/index.html).

    There is also other useful information in Apache Spark documentation site, see the latest version of [Spark SQL and DataFrames](https://spark.apache.org/docs/latest/sql-programming-guide.html), [RDD Programming Guide](https://spark.apache.org/docs/latest/rdd-programming-guide.html), [Structured Streaming Programming Guide](https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html), [Spark Streaming Programming Guide](https://spark.apache.org/docs/latest/streaming-programming-guide.html) and [Machine Learning Library (MLlib) Guide](https://spark.apache.org/docs/latest/ml-guide.html).

    PySpark applications start with initializing `SparkSession` which is the entry point of PySpark as below. In case of running it in PySpark shell via <code>pyspark</code> executable, the shell automatically creates the session in the variable <code>spark</code> for users.
    """)
    return


@app.cell
def _():
    from pyspark.sql import SparkSession

    spark = SparkSession.builder.getOrCreate()
    return (spark,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## DataFrame Creation

    A PySpark DataFrame can be created via `pyspark.sql.SparkSession.createDataFrame` typically by passing a list of lists, tuples, dictionaries and `pyspark.sql.Row`s, a [pandas DataFrame](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html) and an RDD consisting of such a list.
    `pyspark.sql.SparkSession.createDataFrame` takes the `schema` argument to specify the schema of the DataFrame. When it is omitted, PySpark infers the corresponding schema by taking a sample from the data.

    Firstly, you can create a PySpark DataFrame from a list of rows
    """)
    return


@app.cell
def _(spark):
    from datetime import datetime, date
    import pandas as pd
    from pyspark.sql import Row

    df = spark.createDataFrame([
        Row(a=1, b=2., c='string1', d=date(2000, 1, 1), e=datetime(2000, 1, 1, 12, 0)),
        Row(a=2, b=3., c='string2', d=date(2000, 2, 1), e=datetime(2000, 1, 2, 12, 0)),
        Row(a=4, b=5., c='string3', d=date(2000, 3, 1), e=datetime(2000, 1, 3, 12, 0))
    ])
    df
    return date, datetime, df, pd


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Create a PySpark DataFrame with an explicit schema.
    """)
    return


@app.cell
def _(date, datetime, df, spark):
    df_1 = spark.createDataFrame([(1, 2.0, 'string1', date(2000, 1, 1), datetime(2000, 1, 1, 12, 0)), (2, 3.0, 'string2', date(2000, 2, 1), datetime(2000, 1, 2, 12, 0)), (3, 4.0, 'string3', date(2000, 3, 1), datetime(2000, 1, 3, 12, 0))], schema='a long, b double, c string, d date, e timestamp')
    df
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Create a PySpark DataFrame from a pandas DataFrame
    """)
    return


@app.cell
def _(date, datetime, pd, spark):
    pandas_df = pd.DataFrame({'a': [1, 2, 3], 'b': [2.0, 3.0, 4.0], 'c': ['string1', 'string2', 'string3'], 'd': [date(2000, 1, 1), date(2000, 2, 1), date(2000, 3, 1)], 'e': [datetime(2000, 1, 1, 12, 0), datetime(2000, 1, 2, 12, 0), datetime(2000, 1, 3, 12, 0)]})
    df_2 = spark.createDataFrame(pandas_df)
    df_2
    return (df_2,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The DataFrames created above all have the same results and schema.
    """)
    return


@app.cell
def _(df_2):
    # All DataFrames above result same.
    df_2.show()
    df_2.printSchema()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Viewing Data

    The top rows of a DataFrame can be displayed using `DataFrame.show()`.
    """)
    return


@app.cell
def _(df_2):
    df_2.show(1)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Alternatively, you can enable `spark.sql.repl.eagerEval.enabled` configuration for the eager evaluation of PySpark DataFrame in notebooks such as Jupyter. The number of rows to show can be controlled via `spark.sql.repl.eagerEval.maxNumRows` configuration.
    """)
    return


@app.cell
def _(df_2, spark):
    spark.conf.set('spark.sql.repl.eagerEval.enabled', True)
    df_2
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The rows can also be shown vertically. This is useful when rows are too long to show horizontally.
    """)
    return


@app.cell
def _(df_2):
    df_2.show(1, vertical=True)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    You can see the DataFrame's schema and column names as follows:
    """)
    return


@app.cell
def _(df_2):
    df_2.columns
    return


@app.cell
def _(df_2):
    df_2.printSchema()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Show the summary of the DataFrame
    """)
    return


@app.cell
def _(df_2):
    df_2.select('a', 'b', 'c').describe()
    return


@app.cell
def _(df_2):
    df_2.select('a', 'b', 'c').summary()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    `DataFrame.collect()` collects the distributed data to the driver side as the local data in Python. Note that this can throw an out-of-memory error when the dataset is too large to fit in the driver side because it collects all the data from executors to the driver side.
    """)
    return


@app.cell
def _(df_2):
    df_2.collect()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    In order to avoid throwing an out-of-memory exception, use `DataFrame.take()` or `DataFrame.tail()`.
    """)
    return


@app.cell
def _(df_2):
    df_2.take(1)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    PySpark DataFrame also provides the conversion back to a [pandas DataFrame](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html) to leverage pandas API. Note that `toPandas` also collects all data into the driver side that can easily cause an out-of-memory-error when the data is too large to fit into the driver side.
    """)
    return


@app.cell
def _(df_2):
    df_2.toPandas()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Selecting and Accessing Data

    PySpark DataFrame is lazily evaluated and simply selecting a column does not trigger the computation but it returns a `Column` instance.
    """)
    return


@app.cell
def _(df_2):
    df_2.a
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    In fact, most of column-wise operations return `Column`s.
    """)
    return


@app.cell
def _(df_2):
    from pyspark.sql import Column
    from pyspark.sql.functions import upper
    type(df_2.c) == type(upper(df_2.c)) == type(df_2.c.isNull())
    return (upper,)


@app.cell
def _(df_2):
    type(df_2.c)
    return


@app.cell
def _(df_2, upper):
    type(upper(df_2.c))
    return


@app.cell
def _(df_2):
    df_2.c.isNull()
    return


@app.cell
def _(df_2):
    df_2.show()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    These `Column`s can be used to select the columns from a DataFrame. For example, `DataFrame.select()` takes the `Column` instances that returns another DataFrame.
    """)
    return


@app.cell
def _(df_2):
    df_2.select(df_2.c)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Assign new `Column` instance.
    """)
    return


@app.cell
def _(df_2, upper):
    df_2.withColumn('upper_c', upper(df_2.c)).show()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    To select a subset of rows, use `DataFrame.filter()`.
    """)
    return


@app.cell
def _(df_2):
    df_2.filter(df_2.a == 1).show()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Applying a Function

    PySpark supports various UDFs and APIs to allow users to execute Python native functions. See also the latest [Pandas UDFs](https://spark.apache.org/docs/latest/sql-pyspark-pandas-with-arrow.html#pandas-udfs-aka-vectorized-udfs) and [Pandas Function APIs](https://spark.apache.org/docs/latest/sql-pyspark-pandas-with-arrow.html#pandas-function-apis). For instance, the example below allows users to directly use the APIs in [a pandas Series](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.Series.html) within Python native function.
    """)
    return


@app.cell
def _(df_2, pd):
    from pyspark.sql.functions import pandas_udf

    @pandas_udf('long')
    def pandas_plus_one(series: pd.Series) -> pd.Series:
        return series + 1
    df_2.select(pandas_plus_one(df_2.a)).show()  # Simply plus one by using pandas Series.
    return (pandas_udf,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Another example is `DataFrame.mapInPandas` which allows users directly use the APIs in a [pandas DataFrame](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html) without any restrictions such as the result length.
    """)
    return


@app.cell
def _(df_2):
    def pandas_filter_func(iterator):
        for pandas_df in iterator:
            yield pandas_df[pandas_df.a == 1]
    df_2.mapInPandas(pandas_filter_func, schema=df_2.schema).show()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Grouping Data

    PySpark DataFrame also provides a way of handling grouped data by using the common approach, split-apply-combine strategy.
    It groups the data by a certain condition applies a function to each group and then combines them back to the DataFrame.
    """)
    return


@app.cell
def _(spark):
    df_3 = spark.createDataFrame([['red', 'banana', 1, 10], ['blue', 'banana', 2, 20], ['red', 'carrot', 3, 30], ['blue', 'grape', 4, 40], ['red', 'carrot', 5, 50], ['black', 'carrot', 6, 60], ['red', 'banana', 7, 70], ['red', 'grape', 8, 80]], schema=['color', 'fruit', 'v1', 'v2'])
    df_3.show()
    return (df_3,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Grouping and then applying the `avg()` function to the resulting groups.
    """)
    return


@app.cell
def _(df_3):
    df_3.groupby('color').avg().show()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    You can also apply a Python native function against each group by using pandas API.
    """)
    return


@app.cell
def _(df_3):
    def plus_mean(pandas_df):
        return pandas_df.assign(v1=pandas_df.v1 - pandas_df.v1.mean())
    df_3.groupby('color').applyInPandas(plus_mean, schema=df_3.schema).show()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Co-grouping and applying a function.
    """)
    return


@app.cell
def _(pd, spark):
    df1 = spark.createDataFrame(
        [(20000101, 1, 1.0), (20000101, 2, 2.0), (20000102, 1, 3.0), (20000102, 2, 4.0)],
        ('time', 'id', 'v1'))

    df2 = spark.createDataFrame(
        [(20000101, 1, 'x'), (20000101, 2, 'y')],
        ('time', 'id', 'v2'))

    def merge_ordered(l, r):
        return pd.merge_ordered(l, r)

    df1.groupby('id').cogroup(df2.groupby('id')).applyInPandas(
        merge_ordered, schema='time int, id int, v1 double, v2 string').show()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Getting Data In/Out

    CSV is straightforward and easy to use. Parquet and ORC are efficient and compact file formats to read and write faster.

    There are many other data sources available in PySpark such as JDBC, text, binaryFile, Avro, etc. See also the latest [Spark SQL, DataFrames and Datasets Guide](https://spark.apache.org/docs/latest/sql-programming-guide.html) in Apache Spark documentation.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### CSV
    """)
    return


@app.cell
def _(df_3, spark):
    df_3.write.csv('foo.csv', header=True)
    spark.read.csv('foo.csv', header=True).show()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Parquet
    """)
    return


@app.cell
def _(df_3, spark):
    df_3.write.parquet('bar.parquet')
    spark.read.parquet('bar.parquet').show()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### ORC
    """)
    return


@app.cell
def _(df_3, spark):
    df_3.write.orc('zoo.orc')
    spark.read.orc('zoo.orc').show()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Working with SQL

    DataFrame and Spark SQL share the same execution engine so they can be interchangeably used seamlessly. For example, you can register the DataFrame as a table and run a SQL easily as below:
    """)
    return


@app.cell
def _(df_3, spark):
    df_3.createOrReplaceTempView('tableA')
    spark.sql('SELECT count(*) from tableA').show()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    In addition, UDFs can be registered and invoked in SQL out of the box:
    """)
    return


@app.cell
def _(pandas_udf, pd, spark):
    @pandas_udf("integer")
    def add_one(s: pd.Series) -> pd.Series:
        return s + 1

    spark.udf.register("add_one", add_one)
    spark.sql("SELECT add_one(v1) FROM tableA").show()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    These SQL expressions can directly be mixed and used as PySpark columns.
    """)
    return


@app.cell
def _(df_3):
    from pyspark.sql.functions import expr
    df_3.selectExpr('add_one(v1)').show()
    df_3.select(expr('count(*)') > 0).show()
    return


if __name__ == "__main__":
    app.run()
