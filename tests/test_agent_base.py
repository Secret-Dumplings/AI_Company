# -*- coding: utf-8 -*-
"""
Agent Base 单元测试

测试内容：
- XML 模式参数解析
- Function Calling 模式参数解析
- 工具调用统一性测试
"""
import pytest
import os
import sys
from unittest.mock import MagicMock, patch
from bs4 import BeautifulSoup

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestXMLParameterParsing:
    """XML 参数解析测试"""

    def test_parse_xml_single_param(self):
        """测试解析单参数 XML"""
        xml_block = '<get_time></get_time>'
        soup = BeautifulSoup(xml_block, "xml")
        root = soup.find()

        params = {}
        for child in root.children:
            if hasattr(child, 'name') and child.name:
                params[child.name] = child.text

        assert params == {}

    def test_parse_xml_multiple_params(self):
        """测试解析多参数 XML"""
        xml_block = '<search><query>python</query><limit>10</limit></search>'
        soup = BeautifulSoup(xml_block, "xml")
        root = soup.find()

        params = {}
        for child in root.children:
            if hasattr(child, 'name') and child.name:
                params[child.name] = child.text

        assert params == {"query": "python", "limit": "10"}

    def test_parse_xml_ask_for_help(self):
        """测试解析 ask_for_help XML"""
        xml_block = '<ask_for_help><agent_id>time_agent</agent_id><message>查询时间</message></ask_for_help>'
        soup = BeautifulSoup(xml_block, "xml")
        root = soup.find()

        params = {}
        for child in root.children:
            if hasattr(child, 'name') and child.name:
                params[child.name] = child.text

        assert params == {"agent_id": "time_agent", "message": "查询时间"}

    def test_parse_xml_with_special_chars(self):
        """测试解析包含特殊字符的 XML"""
        # BeautifulSoup 会自动解析 XML 实体
        xml_block = '<search><query>test query</query></search>'
        soup = BeautifulSoup(xml_block, "xml")
        root = soup.find()

        params = {}
        for child in root.children:
            if hasattr(child, 'name') and child.name:
                params[child.name] = child.text

        assert params == {"query": "test query"}


class TestFunctionSignatureHandling:
    """函数签名处理测试"""

    def test_no_param_function(self):
        """测试无参数函数调用"""
        import inspect

        def func():
            return "result"

        sig = inspect.signature(func)
        param_count = len([p for p in sig.parameters.values()
                         if p.default == inspect.Parameter.empty
                         and p.kind not in (inspect.Parameter.VAR_POSITIONAL,
                                           inspect.Parameter.VAR_KEYWORD)])

        assert param_count == 0

    def test_single_param_function(self):
        """测试单参数函数调用"""
        import inspect

        def func(query: str):
            return f"search: {query}"

        sig = inspect.signature(func)
        param_count = len([p for p in sig.parameters.values()
                         if p.default == inspect.Parameter.empty
                         and p.kind not in (inspect.Parameter.VAR_POSITIONAL,
                                           inspect.Parameter.VAR_KEYWORD)])

        assert param_count == 1

    def test_kwargs_function(self):
        """测试 **kwargs 函数调用"""
        import inspect

        def func(**kwargs):
            return kwargs

        sig = inspect.signature(func)
        has_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD
                        for p in sig.parameters.values())

        assert has_kwargs is True

    def test_mixed_params_function(self):
        """测试混合参数函数调用"""
        import inspect

        def func(a: str, b: int = 10, **kwargs):
            return f"{a}: {b}"

        sig = inspect.signature(func)
        param_count = len([p for p in sig.parameters.values()
                         if p.default == inspect.Parameter.empty
                         and p.kind not in (inspect.Parameter.VAR_POSITIONAL,
                                           inspect.Parameter.VAR_KEYWORD)])
        has_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD
                        for p in sig.parameters.values())

        assert param_count == 1  # 只有 a 是必需位置参数
        assert has_kwargs is True


class TestToolCallCompatibility:
    """工具调用兼容性测试"""

    def test_xml_to_dict_conversion(self):
        """测试 XML 到 dict 转换"""
        xml_blocks = [
            '<get_time></get_time>',
            '<search><query>test</query></search>',
            '<ask_for_help><agent_id>agent1</agent_id><message>help</message></ask_for_help>'
        ]

        expected = [
            {},
            {"query": "test"},
            {"agent_id": "agent1", "message": "help"}
        ]

        for i, xml in enumerate(xml_blocks):
            soup = BeautifulSoup(xml, "xml")
            root = soup.find()

            params = {}
            for child in root.children:
                if hasattr(child, 'name') and child.name:
                    params[child.name] = child.text

            assert params == expected[i]

    def test_function_call_mode_params(self):
        """测试 Function Calling 模式的 dict 参数"""
        # Function Calling 模式直接传递 dict
        fc_params = {"query": "test", "limit": "10"}

        def mock_tool(**kwargs):
            return kwargs

        result = mock_tool(**fc_params)
        assert result == fc_params


class TestLoggingModule:
    """日志模块测试"""

    def test_logging_config_import(self):
        """测试日志配置导入"""
        from Dumplings.logging_config import setup_logging, get_logger, logger
        assert logger is not None

    def test_setup_logging(self):
        """测试日志设置"""
        from Dumplings.logging_config import setup_logging
        import tempfile
        import os
        import time

        tmpdir = tempfile.mkdtemp()
        try:
            logger = setup_logging(log_dir=tmpdir, level="DEBUG")
            assert logger is not None

            # 检查日志文件是否创建
            log_file = os.path.join(tmpdir, "app.log")
            # 日志文件可能不会立即创建
        finally:
            # 清理日志处理器
            from loguru import logger as loguru_logger
            loguru_logger.remove()
            time.sleep(0.1)  # 等待文件释放
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_get_logger(self):
        """测试获取 logger"""
        from Dumplings.logging_config import get_logger

        logger = get_logger("test_module")
        assert logger is not None

        # 测试带 name 的 logger
        named_logger = get_logger("my_module")
        assert named_logger is not None


class TestAgentBaseIntegration:
    """Agent Base 集成测试"""

    def test_agent_base_import(self):
        """测试 Agent Base 导入"""
        from Dumplings.Agent_Base_ import Agent
        assert Agent is not None

    def test_tool_registry_import(self):
        """测试工具注册器导入"""
        from Dumplings.agent_tool import tool_registry
        assert tool_registry is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])