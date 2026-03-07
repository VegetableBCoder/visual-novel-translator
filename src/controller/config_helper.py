"""
配置管理器临时实现

基于内存的简单配置管理，暂不实现持久化到文件。
TODO: 后续可扩展为基于 JSON 文件的持久化实现。
"""

from typing import Any, Dict
from src.controller.config_interface import IConfigManager


class ConfigHelper(IConfigManager):
    """配置管理器临时实现，基于内存存储"""

    # 默认配置结构
    DEFAULT_CONFIG = {
        "version": "1.0",
        "language": {
            "source": "ja",
            "target": "zh"
        },
        "translation": {
            "engine": "alibaba",
            "alibaba": {
                "access_key_id": "",
                "access_key_secret": ""
            },
            "google": {
                "api_key": ""
            }
        }
    }

    def __init__(self):
        """初始化配置管理器"""
        self._config = self.DEFAULT_CONFIG.copy()

    def load_config(self) -> Dict[str, Any]:
        """
        加载完整配置，返回内存中的配置副本

        Returns:
            配置字典的副本
        """
        return self._config.copy()

    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        保存配置到内存

        TODO: 暂不实现持久化到文件，后续扩展

        Args:
            config: 配置字典

        Returns:
            bool: 保存是否成功
        """
        try:
            # 深拷贝配置到内存
            import copy
            self._config = copy.deepcopy(config)
            return True
        except Exception:
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取嵌套配置值

        Args:
            key: 配置键路径，如 'language.source'
            default: 默认值

        Returns:
            配置项的值，不存在时返回默认值
        """
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """
        设置嵌套配置值

        Args:
            key: 配置键路径，如 'language.source'
            value: 配置值
        """
        keys = key.split('.')
        config = self._config
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value

    def ensure_defaults(self) -> None:
        """
        确保必要的配置项存在

        将默认配置中缺失的项补充到当前配置
        """
        def deep_update(target: Dict, config: Dict):
            """递归更新字典，只添加缺失的键"""
            for k, v in config.items():
                if k not in target:
                    target[k] = v
                elif isinstance(v, dict) and isinstance(target[k], dict):
                    deep_update(target[k], v)

        deep_update(self._config, self.DEFAULT_CONFIG)
