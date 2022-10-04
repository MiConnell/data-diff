import random
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Generator, Sequence, List, Union

from runtype import dataclass

from data_diff.utils import ArithString
from data_diff.databases.database_types import AbstractDialect


@dataclass
class Compiler:
    database: AbstractDialect
    in_select: bool = False  # Compilation runtime flag
    in_join: bool = False  # Compilation runtime flag

    _table_context: List = []  # List[ITable]
    _subqueries: Dict[str, Any] = {}  # XXX not thread-safe
    root: bool = True

    _counter: List = [0]

    def quote(self, s: str):
        return self.database.quote(s)

    def compile(self, elem) -> str:
        res = self._compile(elem)
        if self.root and self._subqueries:
            subq = ", ".join(f"\n  {k} AS ({v})" for k, v in self._subqueries.items())
            self._subqueries.clear()
            return f"WITH {subq}\n{res}"
        return res

    def _compile(self, elem) -> Union[str, "ThreadLocalInterpreter"]:
        if elem is None:
            return "NULL"
        elif isinstance(elem, Compilable):
            return elem.compile(self.replace(root=False))
        elif isinstance(elem, str):
            return elem
        elif isinstance(elem, int):
            return str(elem)
        elif isinstance(elem, datetime):
            return self.database.timestamp_value(elem)
        elif isinstance(elem, bytes):
            return f"b'{elem.decode()}'"
        elif isinstance(elem, ArithString):
            return f"'{elem}'"
        elif isinstance(elem, Generator):
            return ThreadLocalInterpreter(self, elem)
        assert False, elem

    def new_unique_name(self, prefix="tmp"):
        self._counter[0] += 1
        return f"{prefix}{self._counter[0]}"

    def new_unique_table_name(self, prefix="tmp"):
        self._counter[0] += 1
        return f"{prefix}{self._counter[0]}_{'%x'%random.randrange(2**32)}"

    def add_table_context(self, *tables: Sequence):
        return self.replace(_table_context=self._table_context + list(tables))


class Compilable(ABC):
    @abstractmethod
    def compile(self, c: Compiler) -> str:
        ...


class ThreadLocalInterpreter:
    """An interpeter used to execute a sequence of queries within the same thread.

    Useful for cursor-sensitive operations, such as creating a temporary table.
    """

    def __init__(self, compiler: Compiler, gen: Generator):
        self.gen = gen
        self.compiler = compiler

    def interpret(self):
        q = next(self.gen)
        while True:
            try:
                res = yield self.compiler.compile(q)
                q = self.gen.send(res)
            except StopIteration:
                break