# 验证元数据集成

## 概述

验证检查的反馈现在会被记录并包含在最终的 clip spec JSON 中。

## 工作流程

1. **创建草稿** - `draft_clip_spec()`
2. **验证** - `validate_clip_spec()` → 自动记录验证结果
3. **编辑**（如需要）- `edit_draft_spec()`
4. **再次验证** - `validate_clip_spec()` → 记录新的验证结果
5. **提交** - `submit_clip_spec()` → 包含完整验证历史

## 数据结构

### 验证记录格式

每次调用 `validate_clip_spec()` 时，会记录：

```python
{
    "timestamp": "2026-01-29T10:30:00",
    "passed": True,  # 是否通过所有检查
    "results": {
        "layers": [...],      # 每个 layer 的状态和边界框
        "issues": [...],      # 全局问题（重叠、间距、对比度）
        "timing_issues": [...],  # 时序问题
        "canvas": {...},
        "safeZone": {...}
    }
}
```

### 最终 Clip Spec 中的元数据

```json
{
  "durationFrames": 150,
  "layers": [...],
  "composerNotes": "...",
  "validationMetadata": {
    "validation_history": [
      {
        "timestamp": "2026-01-29T10:30:00",
        "passed": false,
        "results": {...}
      },
      {
        "timestamp": "2026-01-29T10:35:00",
        "passed": true,
        "results": {...}
      }
    ],
    "total_validations": 2,
    "final_status": "passed",
    "final_timestamp": "2026-01-29T10:35:00"
  }
}
```

## API

### RAGRecorder 新增方法

```python
from src.tools.rag_recorder import rag_recorder

# 记录验证
rag_recorder.record_validation(
    clip_id="abc123",
    validation_results={...},
    passed=True
)

# 获取验证历史
history = rag_recorder.get_validation_history("abc123")

# 获取元数据格式
metadata = rag_recorder.get_validation_metadata("abc123")

# 清除验证历史
rag_recorder.clear_validations("abc123")
```

## 使用场景

1. **调试** - 查看 clip 经历了多少次验证迭代
2. **质量追踪** - 了解哪些 clips 需要更多调整
3. **性能分析** - 识别验证瓶颈
4. **审计** - 完整的验证历史记录

## 注意事项

- 验证历史在 `submit_clip_spec()` 后会被自动清除
- 如果没有进行过验证，`validationMetadata` 不会出现在 clip spec 中
- 验证历史存储在内存中（RAGRecorder 单例）
