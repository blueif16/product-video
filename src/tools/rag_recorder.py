"""RAG 查询记录器 - 内存缓存"""
from datetime import datetime
from typing import Dict, List, Optional


def extract_and_record_rag_queries(
    agent_result: dict,
    video_project_id: str,
    clip_id: str,
    tool_names: list[str] = None
):
    """
    从 agent 消息历史中提取 RAG 工具调用并记录

    Args:
        agent_result: Agent 执行结果，包含 messages
        video_project_id: 视频项目 ID
        clip_id: Clip ID（planner 可以用 "planning_phase"）
        tool_names: 要提取的工具名称列表，默认为
            ["query_execution_patterns", "query_video_planning_patterns"]
    """
    if tool_names is None:
        tool_names = [
            "query_execution_patterns",
            "query_video_planning_patterns"
        ]

    messages = agent_result.get("messages", [])
    found_rag_calls = 0

    for i, msg in enumerate(messages):
        # 检查是否有工具调用
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tool_call in msg.tool_calls:
                tool_name = tool_call.get("name", "")
                if tool_name in tool_names:
                    args = tool_call.get("args", {})

                    # 找到对应的工具返回结果
                    results = None
                    if i + 1 < len(messages):
                        next_msg = messages[i + 1]
                        if hasattr(next_msg, "content"):
                            content = next_msg.content
                            results = str(content) if content else None

                    rag_recorder.record(
                        video_project_id=video_project_id,
                        clip_id=clip_id,
                        query=args.get("query", ""),
                        match_count=args.get("match_count", 5),
                        results=results,
                        tool_name=tool_name
                    )
                    found_rag_calls += 1

    if found_rag_calls == 0:
        clip_display = clip_id if len(clip_id) <= 8 else clip_id[:8]
        msg = f"   ⚠️  [{clip_display}] No RAG queries found"
        print(msg)

    return found_rag_calls


class RAGRecorder:
    """单例记录器，按 video_project_id 分组存储 RAG 查询"""

    def __init__(self):
        self._cache: Dict[str, List[dict]] = {}

    def record(
        self,
        video_project_id: str,
        clip_id: str,
        query: str,
        match_count: int,
        results: Optional[str] = None,
        tool_name: str = "query_execution_patterns"
    ):
        """记录一次 RAG 查询"""
        if video_project_id not in self._cache:
            self._cache[video_project_id] = []

        self._cache[video_project_id].append({
            "clip_id": clip_id,
            "tool_name": tool_name,
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "match_count": match_count,
            "results": results
        })

    def get_metadata(self, video_project_id: str) -> dict:
        """获取 metadata 格式的记录"""
        queries = self._cache.get(video_project_id, [])

        # 按 clip_id 分组统计
        clips_queries = {}
        for q in queries:
            cid = q["clip_id"]
            if cid not in clips_queries:
                clips_queries[cid] = []
            clips_queries[cid].append({
                "tool_name": q.get("tool_name", "query_execution_patterns"),
                "query": q["query"],
                "timestamp": q["timestamp"],
                "match_count": q["match_count"],
                "results": q.get("results")
            })

        return {
            "rag_queries": queries,
            "rag_queries_by_clip": clips_queries,
            "total_queries": len(queries),
            "clips_with_queries": len(clips_queries)
        }

    def clear(self, video_project_id: str):
        """清除缓存"""
        self._cache.pop(video_project_id, None)


# 全局单例
rag_recorder = RAGRecorder()
