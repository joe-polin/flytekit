import sys
from typing import Iterator, Type

import jsonlines

from flytekit import FlyteContext, Literal, LiteralType
from flytekit.core.type_engine import (
    TypeEngine,
    TypeTransformer,
    TypeTransformerFailedError,
)
from flytekit.models.core import types as _core_types
from flytekit.models.literals import Blob, BlobMetadata, Scalar
from flytekit.types.file import FlyteFile


class JSONIterator:
    def __init__(self, reader: jsonlines.Reader):
        self._reader = reader
        self._reader_iter = reader.iter()

    def __iter__(self):
        return self

    def __next__(self):
        try:
            return next(self._reader_iter)
        except StopIteration:
            self._reader.close()
            raise StopIteration("File handler is exhausted")


print("#########")
print(sys.version_info)
if sys.version_info >= (3, 12):
    type JSON = dict[str, JSON] | list[JSON] | str | int | float | bool | None  # type: ignore[valid-type]
else:
    from typing_extensions import TypeAlias

    JSON: TypeAlias = dict[str, "JSON"] | list["JSON"] | str | int | float | bool | None


class JSONIteratorTransformer(TypeTransformer[Iterator[JSON]]):
    JSON_ITERATOR_FORMAT = "JSONL"

    def __init__(self):
        super().__init__("JSON Iterator", Iterator[JSON])

    def get_literal_type(self, t: Type[JSON]) -> LiteralType:
        return LiteralType(
            blob=_core_types.BlobType(
                format=self.JSON_ITERATOR_FORMAT,
                dimensionality=_core_types.BlobType.BlobDimensionality.SINGLE,
            )
        )

    def to_literal(
        self,
        ctx: FlyteContext,
        python_val: Iterator[JSON],
        python_type: Type[JSON],
        expected: LiteralType,
    ) -> Literal:
        remote_path = FlyteFile.new_remote_file()

        empty = True
        with remote_path.open("w") as fp:
            with jsonlines.Writer(fp) as writer:
                for json_val in python_val:
                    writer.write(json_val)
                    empty = False

        if empty:
            raise ValueError("The iterator is empty.")

        meta = BlobMetadata(
            type=_core_types.BlobType(
                format=self.JSON_ITERATOR_FORMAT,
                dimensionality=_core_types.BlobType.BlobDimensionality.SINGLE,
            )
        )
        return Literal(scalar=Scalar(blob=Blob(metadata=meta, uri=remote_path.path)))

    def to_python_value(self, ctx: FlyteContext, lv: Literal, expected_python_type: Type[JSON]) -> JSONIterator:
        try:
            uri = lv.scalar.blob.uri
        except AttributeError:
            raise TypeTransformerFailedError(f"Cannot convert from {lv} to {expected_python_type}")

        fs = ctx.file_access.get_filesystem_for_path(uri)

        fp = fs.open(uri, "r")
        reader = jsonlines.Reader(fp)

        return JSONIterator(reader)

    def guess_python_type(
        self, literal_type: LiteralType
    ) -> Type[dict[str, JSON]] | Type[list[JSON]] | Type[str] | Type[int] | Type[float] | Type[bool] | Type[None]:
        if (
            literal_type.blob is not None
            and literal_type.blob.dimensionality == _core_types.BlobType.BlobDimensionality.SINGLE
            and literal_type.blob.format == self.JSON_ITERATOR_FORMAT
        ):
            return JSON

        raise ValueError(f"Transformer {self} cannot reverse {literal_type}")


TypeEngine.register(JSONIteratorTransformer())
