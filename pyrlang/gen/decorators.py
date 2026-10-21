# Copyright 2018-2019, Erlang Solutions Ltd, and S2HC Sweden AB
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
# limitations under the License.o
"""
Decorator funcitons for building Gen based classes.

the functions `call`, `cast`, `info` are function decorators.

If you need to overrdide for extra functionality you probably want to use
the classes `CallDecorator`, `CastDecorator`, `InfoDecorator` instead
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any, ParamSpec, TypeAlias, TypeVar, overload

from pyrlang.match import MatchFunction, Pattern

LOG = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pyrlang.gen.server import GenServer

P = ParamSpec("P")
R = TypeVar("R")
Handler: TypeAlias = Callable[..., Coroutine[Any, Any, Any]]
HandlerMatch: TypeAlias = Callable[[Any], tuple[Handler, Any]]


def async_wrapper_factory(fun: Callable[P, R]) -> Callable[P, Coroutine[Any, Any, R]]:
    async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return fun(*args, **kwargs)

    return async_wrapper


class HandleDecorator:
    """
    Base class for handler Decorators, don't use directly
    """

    handler_type: str | None = None

    def __init__(
        self, order: int | MatchFunction, pattern: MatchFunction | None = None
    ) -> None:
        if not pattern:
            import warnings

            warnings.warn(DeprecationWarning("you should specify order"))
            if isinstance(order, int):
                raise TypeError("handler pattern must be callable")
            pattern = order
            # high but not ensured highest this should be
            # removed soon anyway
            order = 999

        if not isinstance(order, int):
            raise TypeError("handler order must be an integer")
        if not callable(pattern):
            raise TypeError("handler pattern must be callable")
        self.order = order
        self.pattern = pattern

    @overload
    def __call__(
        self, fun: Callable[P, Coroutine[Any, Any, R]]
    ) -> Callable[P, Coroutine[Any, Any, R]]: ...

    @overload
    def __call__(self, fun: Callable[P, R]) -> Callable[P, Coroutine[Any, Any, R]]: ...

    def __call__(self, fun: Callable[..., Any]) -> Handler:
        if not inspect.iscoroutinefunction(fun):
            LOG.debug(
                "function %s is a handle_%s and is not async", fun, self.handler_type
            )
            fun = async_wrapper_factory(fun)

        run_fun = self._pattern_run_fun_factory(fun)
        fun.__dict__.update(
            _gen_handler=self.handler_type,
            _gen_pattern=Pattern(self.pattern, run_fun),
            _gen_order=self.order,
        )
        return fun

    @staticmethod
    def _pattern_run_fun_factory(fun: Handler) -> HandlerMatch:
        """
        Factory function for generating the run function of a pattern.

        Used by `HandleDecorator`
        :param fun: the function that should inject into the return
        :return: function that take msg in and return (fun, msg)
        """

        def _simple_pattern_run_fun(msg: Any) -> tuple[Handler, Any]:
            return fun, msg

        return _simple_pattern_run_fun


class CallDecorator(HandleDecorator):
    """
    handle_call decorator, decorate functions that should be part of the
    handle_call matching
    """

    handler_type = "call"

    @staticmethod
    def _pattern_run_fun_factory(fun: Handler) -> HandlerMatch:

        async def _handle_reply_wrapper(gs_instance: GenServer, msg: Any) -> None:
            """
            wrapper function to strip a Atom('$gen_call') message to
            the actual message, then send a reply
            :param msg: 3 (Atom('$gen_call'), (sender, mref), message)
            :return: function that takes a message
            """
            (sender, mref) = msg[1]
            res = await fun(gs_instance, msg[2])
            n = gs_instance.get_node()
            pid = gs_instance.pid_
            await n.send(pid, sender, (mref, res))

        return lambda msg: (_handle_reply_wrapper, msg)


def call(
    order: int | MatchFunction, pattern: MatchFunction | None = None
) -> CallDecorator:
    """wrapper function around the `CallDecorator` class"""
    return CallDecorator(order, pattern)


class CastDecorator(HandleDecorator):
    """
    handle_cast decorator, decorate functions that should be part of the
    handle_cast matching
    """

    handler_type = "cast"

    @staticmethod
    def _pattern_run_fun_factory(fun: Handler) -> HandlerMatch:
        """
        Factory function for generating the run function of a pattern.

        Used by `HandleDecorator`
        :param fun: the function that should inject into the return
        :return: function that take msg in and return (fun, msg)
        """

        def _simple_pattern_run_fun(msg: Any) -> tuple[Handler, Any]:
            """
            we strip the Atom('gen_cast') from the message
            :param msg:
            :return:
            """
            return fun, msg[1]

        return _simple_pattern_run_fun


def cast(
    order: int | MatchFunction, pattern: MatchFunction | None = None
) -> CastDecorator:
    """wrapper function around the `CastDecorator` class"""
    return CastDecorator(order, pattern)


class InfoDecorator(HandleDecorator):
    """
    handle_info decorator, decorate functions that should be part of the
    handle_info matching
    """

    handler_type = "info"


def info(
    order: int | MatchFunction, pattern: MatchFunction | None = None
) -> InfoDecorator:
    """wrapper function around the `InfoDecorator` class"""
    return InfoDecorator(order, pattern)
