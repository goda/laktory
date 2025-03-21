import pyspark.sql.types as T

DATATYPES_MAP = {
    "binary": T.BinaryType(),
    "byte": T.ByteType(),
    "int8": T.ByteType(),
    "tinyint": T.ByteType(),
    "short": T.ShortType(),
    "int16": T.ShortType(),
    "smallint": T.ShortType(),
    "int": T.IntegerType(),
    "int32": T.IntegerType(),
    "long": T.LongType(),
    "int64": T.LongType(),
    "bigint": T.LongType(),
    "float": T.FloatType(),
    "float32": T.FloatType(),
    "double": T.DoubleType(),
    "float64": T.DoubleType(),
    "boolean": T.BooleanType(),
    "string": T.StringType(),
    "utf8": T.StringType(),
    "date": T.DateType(),
    "timestamp": T.TimestampType(),
    "datetime": T.TimestampType(),
    # "struct<>": T.StructType(),
    # "struct": T.StructType(),
    # "array": T.ArrayType(),
    # "list": T.ArrayType(),
}
