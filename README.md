# Research Paper Agent

一个用于课程演示的单用途 AI Agent：它从 `papers/` 中读取本地 PDF，并在需要时检索网页资料，再用模型给出带证据的中文回答。

## 作业要求对应

| 作业要求 | 本项目实现 |
| --- | --- |
| 至少两个技能 | `read_local_pdf` 读取和筛选本地 PDF；`web_research` 调用 DuckDuckGo 公共检索 API。另有 `available_papers`。 |
| MCP 或函数调用 | `mcp_server.py` 是标准 MCP stdio 服务；`agent.py` 使用 LLM JSON Schema 函数调用循环编排工具。 |
| Vibe Coding | 保留用于生成项目的提示词、AI 初稿与后续调试记录；学生重点负责提示词、边界和实验设计。 |

## 安装

```powershell
cd E:\research-paper-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

将 API Key 填入 `.env`。把任意可复制的 PDF 放进 `papers/` 文件夹。

## 运行 Agent

```powershell
python agent.py "阅读论文并概括研究问题、方法和实验结果。"
python agent.py "这篇论文与 Transformer 原始论文有哪些关键差异？"
```

若 PDF 名称不在问题里，模型会根据工具先获取证据；为了提高成功率，可写明：`请阅读 xxx.pdf 并总结方法。`

## 运行 MCP 服务

```powershell
python mcp_server.py
```

在支持 MCP 的桌面客户端配置中添加：

```json
{
  "mcpServers": {
    "research-paper-agent": {
      "command": "E:\\research-paper-agent\\.venv\\Scripts\\python.exe",
      "args": ["E:\\research-paper-agent\\mcp_server.py"]
    }
  }
}
```

## 测试

```powershell
python -m pytest -q
```

## 演示脚本

1. 将一篇论文放入 `papers/`，询问“总结 xxx.pdf 的方法与实验结果”。
2. 询问“该方法与相关经典工作有什么差异？”——观察 Agent 先读 PDF、再调用网页检索。
3. 断开网络或询问 PDF 不包含的信息，展示它会报告证据不足而不是编造。

## 系统提示词设计

Agent 的提示词位于 `agent.py`。其核心规则为：本地论文问题必须使用 PDF 工具；背景问题使用网页工具；最终结果把结论与证据分开，并包含页码或 URL。这让项目能清楚证明它依赖外部上下文，而非只依赖模型知识。
