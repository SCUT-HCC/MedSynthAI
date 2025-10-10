"""
全局评分历史管理器

用于存储和管理各轮次的评分历史，支持第一轮不传入historical_scores的需求
"""

from typing import Dict, List, Any

class ScoreHistoryManager:
    """
    评分历史管理器
    
    单例模式实现，用于全局管理评分历史数据
    """
    
    _instance = None
    _history: Dict[str, List[Dict[str, Any]]] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化评分历史管理器"""
        if not hasattr(self, '_initialized'):
            self._initialized = True
    
    def clear_history(self, session_id: str = "default"):
        """清除指定会话的历史记录"""
        if session_id in self._history:
            del self._history[session_id]
    
    def clear_all_history(self):
        """清除所有历史记录"""
        self._history.clear()
    
    def add_round_score(self, round_number: int, scores: Dict[str, float], session_id: str = "default"):
        """
        添加一轮评分到历史记录
        
        Args:
            round_number: 轮次编号
            scores: 该轮的评分字典
            session_id: 会话ID，用于区分不同对话
        """
        if session_id not in self._history:
            self._history[session_id] = []
        
        self._history[session_id].append({
            'round': round_number,
            'scores': scores,
            'timestamp': None  # 可以添加时间戳
        })
    
    def get_historical_scores(self, current_round: int, session_id: str = "default") -> Dict[str, float]:
        """
        获取历史评分（不包括当前轮）
        
        Args:
            current_round: 当前轮次
            session_id: 会话ID
            
        Returns:
            Dict[str, float]: 历史评分汇总，如果第一轮返回空字典
        """
        if session_id not in self._history or current_round <= 1:
            return {}
        
        # 返回所有历史轮次的评分
        # 这里可以设计更复杂的逻辑，如返回平均值、最新值等
        if self._history[session_id]:
            # 返回最新一轮的评分作为参考
            latest_scores = self._history[session_id][-1]['scores']
            return latest_scores
        
        return {}
    
    def get_all_history(self, session_id: str = "default") -> List[Dict[str, Any]]:
        """获取完整的评分历史"""
        return self._history.get(session_id, [])
    
    def get_round_score(self, round_number: int, session_id: str = "default") -> Dict[str, float]:
        """获取指定轮次的评分"""
        if session_id not in self._history:
            return {}
        
        for record in self._history[session_id]:
            if record['round'] == round_number:
                return record['scores']
        
        return {}

# 创建全局实例
score_history_manager = ScoreHistoryManager()