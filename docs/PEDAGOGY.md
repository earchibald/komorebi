# Komorebi: The Pedagogical Master Ledger
*A Living Textbook for Human & Agentic Understanding*

---

## 1. Zero-Friction Ingestion & "Messy Chunks"
Traditional productivity tools fail because they demand structured data (titles, tags, priorities) during operational crises—exactly when users have the least time to provide them.

### The Philosophy: Capture Now, Refine Later
Komorebi implements a **"Capture-First"** architecture. We treat every input as a "Messy Chunk." Whether it's a 50MB terminal log, a half-written note, or a link to a GitHub PR, the system accepts it immediately and offloads the "Organization Debt" to a background worker.

### Logic: The "Auto-Sense" Pipe
The CLI must detect when it is receiving piped data (`stdin`) and decide whether to process it synchronously or move it to a background worker based on size to prevent terminal "hang."

```python
# cli/main.py logic snippet
import sys

def add_task(content: str = None):
    # Detect pipe: cat log.txt | komorebi add
    if not sys.stdin.isatty():
        raw_data = sys.stdin.read()
        if len(raw_data) > 10_000: # 10KB Threshold
            # Hand off to FastAPI Background Task via 202 Accepted
            api.post("/ingest/async", json={"raw": raw_data})
            print("🌊 Large stream detected. Processing in background...")
        else:
            process_sync(raw_data)
```

---

## 2. Contextual Memory: Recursive Summarization (RLM)
Even local LLMs hit the "Context Wall" (8k–128k tokens). Once a window is saturated, the model's "attention" atrophies, leading to "Lost in the Middle" syndrome.

### The Concept: The Hierarchical Pyramid
We use Recursive Language Modeling (RLM). Instead of truncating old data, we treat the context as a pyramid. We summarize the bottom layer (Raw Data) into a middle layer (Atomic Summaries), and then summarize those into a "Global Context" anchor.

### Logic: The Summarization Loop
We use a Map-Reduce pattern. We "Map" summaries to chunks and "Reduce" them into a single Global Context.

```python
# backend/app/core/compactor.py
async def recursive_compress(text: str, target_tokens: int = 500) -> str:
    current_tokens = count_tokens(text)
    if current_tokens <= target_tokens:
        return text

    # Layer 1: Partition into 2000-token chunks
    chunks = partition_text(text, chunk_size=2000)
    
    # Layer 2: Summarize each chunk with a 'Goal Anchor'
    summaries = []
    for chunk in chunks:
        # The 'Anchor' prevents the 'Telephone Game' effect (meaning drift)
        s = await llm.summarize(
            chunk, 
            system_prompt="Summarize this log while preserving the Primary Goal: [Project Context]"
        )
        summaries.append(s)

    # Recurse: Re-summarize the summaries until target_size is met
    combined = "\n".join(summaries)
    return await recursive_compress(combined, target_tokens)
```

---

## 3. The Hookable MCP Aggregator
We don't want to build "Integrations"; we want to build a Muxer. Komorebi acts as an MCP Aggregator (Host of Hosts), muxing external MCP servers (GitHub, Jira, etc.) into a single interface.

### Logic: Secure Auth Provider
To keep this "Operational Grade," we never store keys in plain text. We use a Modular Secret Provider to inject credentials into child processes ONLY at the moment of execution.

```python
# backend/app/mcp/auth.py
from abc import ABC, abstractmethod

class SecretProvider(ABC):
    @abstractmethod
    def get_secret(self, key_uri: str) -> str:
        pass

class KeyringProvider(SecretProvider):
    def get_secret(self, key_uri: str):
        import keyring
        return keyring.get_password("komorebi-mcp", key_uri)

class OnePasswordProvider(SecretProvider):
    def get_secret(self, key_uri: str):
        # Implementation using 'op read'
        return subprocess.check_output(["op", "read", key_uri]).decode().strip()
```

---

## 4. The Elicitation Queue & UI State
If the LLM is unsure how to categorize a "Messy Chunk," it doesn't guess—it Elicits more information via a "Context Gap" notification.

### Logic: SSE & Signals
The UI uses Server-Sent Events (SSE) and React Signals to provide a real-time, high-density dashboard. SSE allows the backend to "push" a gap to the UI without a full WebSocket overhead.

```typescript
// frontend/src/store/signals.ts
import { signal } from "@preact/signals-react";

export const metrics = signal({ tps: 0, latency: 0, queueSize: 0 });
export const elicitationQueue = signal<any[]>([]);

// SSE listener for background worker updates
const sse = new EventSource("/api/events/worker-status");
sse.onmessage = (e) => {
    const data = JSON.parse(e.data);
    if (data.type === "METRIC_UPDATE") metrics.value = { ...metrics.value, ...data.payload };
    if (data.type === "ELICITATION_REQUIRED") elicitationQueue.value = [data.payload, ...elicitationQueue.value];
};
```

---

## 5. Benchmarking & Governance (The Hammer)
Komorebi must remain performant under "Operational Load." We stress-test using synthetic, high-volume data.

### Logic: Tokenization Efficiency (TE)
We analyze the ratio of characters to tokens to ensure that messy logs (hex codes, terminal escapes) aren't causing a "token explosion" in our database.

```python
# scripts/hammer_gen.py
def calculate_token_efficiency(raw_text: str, token_count: int):
    # Optimal ratio is ~4 chars per token for English text
    expected_tokens = len(raw_text) / 4
    efficiency = expected_tokens / token_count
    return efficiency # > 1.0 is efficient; < 0.5 indicates 'noisy' logs
```

---

### 6. Collected Reference Library (Annotated)

#### Foundations & Ingestion
* [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/): Non-blocking execution patterns.
* [Streamlining Python Task Management](https://www.youtube.com/watch?v=N4f8-pG-17o): Core philosophical project anchor.
* [shtab GitHub Repository](https://github.com/iterative/shtab): Tooling for native CLI completion.

#### AI & Recursive Summarization
* [Recursive Language Models (MIT Research)](https://alexzhang13.github.io/blog/2025/rlm/): Theory of context-as-code.
* [Recursive Summarization Logic (Video)](https://www.youtube.com/watch?v=8qcZRrAKsMY): Practical Map-Reduce loop walkthrough.
* [Taming LLMs with Pydantic Parsing](https://www.youtube.com/watch?v=eIy2aBPIg2g): How we validate messy logs into clean schemas.
* [How to stream LLM responses in Python](https://www.youtube.com/watch?v=7p_50E2uF6s): The logic for CLI/UI "Live" output.
* [Recursive Language Model — Destroys the context window limit (Video)](https://www.youtube.com/watch?v=8qcZRrAKsMY)
* [Recursive Summarization and the Context Window (Video)](https://www.youtube.com/watch?v=OUjkukMf9UU)

#### Connectivity & MCP
* [MCP Specification](https://modelcontextprotocol.io/specification/2025-11-25): The "Muxer" contract for tools and resources.
* [Building an MCP Server with Python](https://www.youtube.com/watch?v=Ywy9x8gM410): Essential for implementation.
* [Model Context Protocol Explained (Video)](https://www.youtube.com/watch?v=pieK0dog66Q)

#### Frontend & Metrics
* [Signals in React (Video)](https://www.youtube.com/watch?v=pieK0dog66Q): Fine-grained reactivity for dashboards.
* [NVIDIA GenAI-Perf](https://developer.nvidia.com/blog/llm-benchmarking-fundamental-concepts/): Benchmarking metrics for TTFT and TPS.
* [TanStack Query](https://tanstack.com/query/latest): Managing server state and async data.
* [Build a task manager AI agent using LLM (Video)](https://www.youtube.com/watch?v=HfXMkoUCTyE)
