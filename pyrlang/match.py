# Copyright 2018, Erlang Solutions Ltd, and S2HC Sweden AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, Literal, TypeAlias, TypeVar

MatchFunction: TypeAlias = Callable[[Any], bool]
RunFunction: TypeAlias = Callable[[Any], Any]
PatternInput: TypeAlias = "Pattern | tuple[MatchFunction | None, RunFunction | None]"
T = TypeVar("T")


def _make_pattern(p: PatternInput) -> Pattern:
    if isinstance(p, Pattern):
        return p
    return Pattern(*p)


def _simple_match(data: Any) -> bool:
    return True


def _simple_run(data: T) -> T:
    return data


class Match:
    """
    Match class to mimic an aid in the erlang pattern matching used in calls
    and, in our case more importantly, in receive
    """

    def __init__(self, patterns: Iterable[PatternInput] | None = None) -> None:
        if not patterns:
            # make catch all that returns raw data
            patterns = [(None, None)]
        self._patterns = [_make_pattern(p) for p in patterns]

    def __call__(self, data: Any) -> Pattern | Literal[False]:
        for p in self._patterns:
            if not p.match(data):
                continue
            return p
        return False

    def match(self, data: Any) -> Pattern | Literal[False]:
        return self(data)


class Pattern:
    def __init__(
        self, match_fun: MatchFunction | None = None, run_fun: RunFunction | None = None
    ) -> None:
        if not match_fun:
            match_fun = _simple_match

        if not run_fun:
            run_fun = _simple_run

        if not callable(match_fun):
            raise TypeError(f"match fun {match_fun} not callable")
        if not callable(run_fun):
            raise TypeError(f"run fun {run_fun} not callable")
        self.__match_fun = match_fun
        self.__run_fun = run_fun

    def match(self, data: Any) -> bool:
        return self.__match_fun(data)

    def run(self, data: Any) -> Any:
        return self.__run_fun(data)
