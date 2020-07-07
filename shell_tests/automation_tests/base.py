import unittest
from abc import abstractmethod
from typing import Type

from shell_tests.configs import TestsConfig
from shell_tests.handlers.resource_handler import ResourceHandler
from shell_tests.helpers.handler_storage import HandlerStorage


class BaseTestCase(unittest.TestCase):
    def _add_decorator_for_expect_failed_func(
        self, method_name: str, tests_conf: TestsConfig
    ):
        test_name = f"{type(self).__name__}.{method_name}"
        reason = tests_conf.expected_failures.get(test_name)
        if reason:
            func = getattr(self, method_name)
            wrapped_func = self._expect_failure(func, reason)
            setattr(self, method_name, wrapped_func)

    def _expect_failure(self, func, expected_message):
        def wrapped(*args, **kwargs):
            with self.assertRaisesRegexp(Exception, expected_message):
                func(*args, **kwargs)

        return wrapped

    def id(self):  # noqa: A003
        raise NotImplementedError("You have to create unique id for the test")


class BaseResourceServiceTestCase(BaseTestCase):
    def __init__(
        self,
        method_name: str,
        handler: ResourceHandler,
        handler_storage: HandlerStorage,
    ):
        """Base Resource and Service Test Case."""
        super().__init__(method_name)
        self.handler = handler
        self.handler_storage = handler_storage
        self._add_decorator_for_expect_failed_func(method_name, handler.conf.tests_conf)

    def id(self):  # noqa: A003
        id_ = unittest.TestCase.id(self)
        return f"{id_}-{self.handler.name}"


class BaseSandboxTestCase(BaseTestCase):
    def __init__(self, method_name, sandbox_handler):
        """Base Sandbox Test Case."""
        super().__init__(method_name)
        self.sandbox_handler = sandbox_handler
        self._add_decorator_for_expect_failed_func(
            method_name, sandbox_handler.tests_conf
        )

    def id(self):  # noqa: A003
        id_ = unittest.TestCase.id(self)
        return f"{id_}-{self.sandbox_handler.name}"


class OptionalTestCase:
    @property
    @abstractmethod
    def test_case(self) -> Type[BaseResourceServiceTestCase]:
        raise NotImplementedError

    @abstractmethod
    def is_suitable(self, handler, handler_storage: HandlerStorage) -> bool:
        raise NotImplementedError
