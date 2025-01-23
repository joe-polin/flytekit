import typing
import asyncio
import datetime
from flytekit.core.context_manager import FlyteContext, FlyteContextManager

from flytekit.core.type_engine import (
    AsyncTypeTransformer,
    TypeEngine,
)
from flytekit.models.literals import (
    Literal,
    Primitive,
    Scalar,
)
from flytekit.models.types import LiteralType, SimpleType

T = typing.TypeVar("T")


class MyInt:
    def __init__(self, x: int):
        self.val = x

    def __eq__(self, other):
        if not isinstance(other, MyInt):
            return False
        return other.val == self.val


class MyIntAsyncTransformer(AsyncTypeTransformer[MyInt]):
    def __init__(self):
        super().__init__(name="MyAsyncInt", t=MyInt)

    def assert_type(self, t, v):
        return

    def get_literal_type(self, t: typing.Type[MyInt]) -> LiteralType:
        return LiteralType(simple=SimpleType.INTEGER)

    async def async_to_literal(
        self,
        ctx: FlyteContext,
        python_val: MyInt,
        python_type: typing.Type[MyInt],
        expected: LiteralType,
    ) -> Literal:
        print(f"start waiting on {python_val.val} {datetime.datetime.now()}")
        await asyncio.sleep(1)
        print(f"done waiting on {python_val.val} {datetime.datetime.now()}")
        return Literal(scalar=Scalar(primitive=Primitive(integer=python_val.val)))

    async def async_to_python_value(
        self, ctx: FlyteContext, lv: Literal, expected_python_type: typing.Type[MyInt]
    ) -> MyInt:
        return MyInt(lv.scalar.primitive.integer)

    def guess_python_type(self, literal_type: LiteralType) -> typing.Type[MyInt]:
        return MyInt


def test_file_formats_getting_literal_type():
    TypeEngine.register(MyIntAsyncTransformer())

    lt = LiteralType(simple=SimpleType.INTEGER)
    python_val = [MyInt(10), MyInt(11), MyInt(12), MyInt(13), MyInt(14)]
    ctx = FlyteContext.current_context()

    xx = TypeEngine.to_literal(ctx, python_val, typing.List[MyInt], lt)

    del TypeEngine._REGISTRY[MyInt]

