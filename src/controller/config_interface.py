"""
配置管理器抽象接口

定义配置管理的统一接口，支持依赖倒置设计。
界面层依赖于此接口，而非具体实现。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class IConfigManager(ABC):
    """配置管理器抽象接口"""

    @abstractmethod
    def load_config(self) -> Dict[str, Any]:
        """
        加载完整配置，返回字典

        Returns:
            配置字典
        """
        pass

    @abstractmethod
    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        保存配置到持久化存储

        Args:
            config: 配置字典

        Returns:
            bool: 保存是否成功
        """
        pass

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项的值，支持点号分隔的路径如 'language.source'

        Args:
            key: 配置键路径，如 'language.source'
            default: 默认值

        Returns:
            配置项的值，不存在时返回默认值
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """
        设置配置项的值，支持点号分隔的路径

        Args:
            key: 配置键路径，如 'language.source'
            value: 配置值
        """
        pass

    @abstractmethod
    def ensure_defaults(self) -> None:
        """
        确保默认配置存在
        将默认配置中缺失的项补充到当前配置
        """
        pass
