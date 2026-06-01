"""
Redis 去重模块
使用 hashlib MD5 + Redis SADD 实现计费记录去重
key: jf:filter
"""
import hashlib
import json
import redis
import config


class RedisFilter:
    """Redis 去重过滤器 — 基于 Set 数据结构"""

    def __init__(self):
        self.client = redis.Redis(**config.REDIS_CONFIG)
        self.filter_key = config.REDIS_FILTER_KEY  # jf:filter

    def _make_md5(self, data) -> str:
        """使用 hashlib 生成 MD5 哈希"""
        if isinstance(data, (dict, list)):
            # 排序 key 保证一致性
            data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        else:
            data_str = str(data)
        return hashlib.md5(data_str.encode('utf-8')).hexdigest()

    def is_duplicate(self, record_data: dict) -> bool:
        """
        检查计费记录是否重复
        返回 True = 重复（已存在），False = 新记录
        """
        md5_hash = self._make_md5(record_data)
        added = self.client.sadd(self.filter_key, md5_hash)
        # sadd 返回 1 → 新元素已添加, 0 → 元素已存在
        return added == 0

    def check_and_add(self, record_data: dict) -> tuple:
        """
        检查并添加到去重集合
        返回 (is_duplicate: bool, md5_hash: str)
        """
        md5_hash = self._make_md5(record_data)
        added = self.client.sadd(self.filter_key, md5_hash)
        return (added == 0), md5_hash

    def remove_hash(self, md5_hash: str):
        """从去重集合中移除某个哈希（删除记录时调用）"""
        self.client.srem(self.filter_key, md5_hash)

    def clear_all(self):
        """清空去重集合（慎用）"""
        self.client.delete(self.filter_key)

    def get_count(self) -> int:
        """获取去重集合中的元素数量"""
        return self.client.scard(self.filter_key)

    def exists(self, record_data: dict) -> bool:
        """仅检查是否存在，不添加"""
        md5_hash = self._make_md5(record_data)
        return self.client.sismember(self.filter_key, md5_hash)

    def ping(self) -> bool:
        """测试 Redis 连接"""
        try:
            return self.client.ping()
        except Exception:
            return False


# 全局单例
redis_filter = RedisFilter()
