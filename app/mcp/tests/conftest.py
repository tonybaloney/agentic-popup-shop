"""
Pytest configuration and fixtures for MCP server testing.

This module provides shared fixtures and configuration for all MCP server tests.
"""

import pytest
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for the test session.
    
    This fixture provides a single event loop for all async tests in the session.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
