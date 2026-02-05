#!/usr/bin/env python3
"""Komorebi Hammer - Load testing and benchmarking script.

This script exercises the backend API to validate performance
and correctness under load. It is the success criteria for
the Komorebi implementation.

Usage:
    python scripts/hammer_gen.py [--base-url URL] [--chunks N] [--projects N]
"""

import argparse
import asyncio
import random
import string
import time
from dataclasses import dataclass
from typing import Optional

import httpx


@dataclass
class HammerResult:
    """Results from a hammer run."""
    
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_time_seconds: float
    requests_per_second: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    
    def __str__(self) -> str:
        return f"""
╔══════════════════════════════════════════════════════════════╗
║                    KOMOREBI HAMMER RESULTS                   ║
╠══════════════════════════════════════════════════════════════╣
║  Total Requests:     {self.total_requests:>8}                            ║
║  Successful:         {self.successful_requests:>8}                            ║
║  Failed:             {self.failed_requests:>8}                            ║
╠══════════════════════════════════════════════════════════════╣
║  Total Time:         {self.total_time_seconds:>8.2f}s                           ║
║  Requests/Second:    {self.requests_per_second:>8.2f}                           ║
╠══════════════════════════════════════════════════════════════╣
║  Avg Latency:        {self.avg_latency_ms:>8.2f}ms                          ║
║  Min Latency:        {self.min_latency_ms:>8.2f}ms                          ║
║  Max Latency:        {self.max_latency_ms:>8.2f}ms                          ║
╚══════════════════════════════════════════════════════════════╝
"""


def generate_random_content() -> str:
    """Generate random chunk content."""
    templates = [
        "Need to implement {feature} for the {component} module",
        "Bug fix: {issue} in the {area} functionality",
        "Research: Look into {topic} for better performance",
        "Meeting notes: Discussed {topic} with the team",
        "TODO: Refactor {component} to use {pattern} pattern",
        "Idea: What if we used {technology} for {purpose}?",
        "Review: Check the {component} code for {issue}",
        "Deploy: Need to push {feature} to {environment}",
    ]
    
    features = ["authentication", "caching", "logging", "metrics", "SSE", "MCP integration"]
    components = ["backend", "frontend", "CLI", "database", "API", "core"]
    topics = ["recursive summarization", "token optimization", "signal state", "async patterns"]
    issues = ["memory leak", "race condition", "validation error", "timeout"]
    patterns = ["repository", "factory", "observer", "strategy"]
    technologies = ["Redis", "GraphQL", "WebSockets", "gRPC"]
    areas = ["compaction", "capture", "sync", "search"]
    environments = ["staging", "production", "testing"]
    purposes = ["real-time updates", "better caching", "improved UX"]
    
    template = random.choice(templates)
    content = template.format(
        feature=random.choice(features),
        component=random.choice(components),
        topic=random.choice(topics),
        issue=random.choice(issues),
        pattern=random.choice(patterns),
        technology=random.choice(technologies),
        area=random.choice(areas),
        environment=random.choice(environments),
        purpose=random.choice(purposes),
    )
    
    # Add some additional context sometimes
    if random.random() > 0.5:
        words = ["this", "will", "help", "understand", "context", "better", "for", "the", "task", "ahead", "important", "note", "remember"]
        content += f"\n\nAdditional context: {' '.join(random.choices(words, k=10))}"
    
    return content


def generate_explosion_content(index: int, target_size: int = 1024) -> str:
    """Generate padded content to force context explosion."""
    base = (
        f"Log entry {index}: pipeline spike detected. "
        f"[ERROR] Traceback {index} at worker.py:{index}. "
        "Retrying with exponential backoff. "
    )
    padding_size = max(0, target_size - len(base))
    return base + ("x" * padding_size)


def generate_random_tags() -> list[str]:
    """Generate random tags."""
    available_tags = [
        "urgent", "backend", "frontend", "bug", "feature", 
        "research", "docs", "refactor", "security", "performance",
        "ux", "api", "database", "testing", "deployment",
    ]
    return random.sample(available_tags, k=random.randint(0, 4))


class KomorebiHammer:
    """Load tester for the Komorebi backend."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/api/v1"
        self.latencies: list[float] = []
        self.successes = 0
        self.failures = 0
    
    async def check_health(self) -> bool:
        """Check if the server is healthy."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/health", timeout=5.0)
                return response.status_code == 200
            except Exception:
                return False
    
    async def create_project(self, name: str, description: Optional[str] = None) -> Optional[str]:
        """Create a project and return its ID."""
        async with httpx.AsyncClient() as client:
            try:
                start = time.perf_counter()
                response = await client.post(
                    f"{self.api_url}/projects",
                    json={"name": name, "description": description},
                    timeout=10.0,
                )
                elapsed = (time.perf_counter() - start) * 1000
                
                self.latencies.append(elapsed)
                
                if response.status_code == 201:
                    self.successes += 1
                    return response.json()["id"]
                else:
                    self.failures += 1
                    return None
                    
            except Exception as e:
                self.failures += 1
                print(f"Error creating project: {e}")
                return None
    
    async def capture_chunk(
        self,
        content: str,
        project_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> bool:
        """Capture a chunk."""
        async with httpx.AsyncClient() as client:
            try:
                data = {
                    "content": content,
                    "source": "hammer",
                }
                if project_id:
                    data["project_id"] = project_id
                if tags:
                    data["tags"] = tags
                
                start = time.perf_counter()
                response = await client.post(
                    f"{self.api_url}/chunks",
                    json=data,
                    timeout=10.0,
                )
                elapsed = (time.perf_counter() - start) * 1000
                
                self.latencies.append(elapsed)
                
                if response.status_code == 201:
                    self.successes += 1
                    return True
                else:
                    self.failures += 1
                    print(f"Chunk creation failed: {response.status_code} - {response.text}")
                    return False
                    
            except Exception as e:
                self.failures += 1
                print(f"Error capturing chunk: {e}")
                return False
    
    async def list_chunks(self, limit: int = 10) -> bool:
        """List chunks."""
        async with httpx.AsyncClient() as client:
            try:
                start = time.perf_counter()
                response = await client.get(
                    f"{self.api_url}/chunks",
                    params={"limit": limit},
                    timeout=10.0,
                )
                elapsed = (time.perf_counter() - start) * 1000
                
                self.latencies.append(elapsed)
                
                if response.status_code == 200:
                    self.successes += 1
                    return True
                else:
                    self.failures += 1
                    return False
                    
            except Exception as e:
                self.failures += 1
                print(f"Error listing chunks: {e}")
                return False
    
    async def get_stats(self) -> bool:
        """Get chunk statistics."""
        async with httpx.AsyncClient() as client:
            try:
                start = time.perf_counter()
                response = await client.get(
                    f"{self.api_url}/chunks/stats",
                    timeout=10.0,
                )
                elapsed = (time.perf_counter() - start) * 1000
                
                self.latencies.append(elapsed)
                
                if response.status_code == 200:
                    self.successes += 1
                    return True
                else:
                    self.failures += 1
                    return False
                    
            except Exception as e:
                self.failures += 1
                print(f"Error getting stats: {e}")
                return False
    
    async def run_benchmark(
        self,
        num_projects: int = 3,
        num_chunks: int = 50,
        concurrent_requests: int = 5,
    ) -> HammerResult:
        """Run the full benchmark suite."""
        print("🔨 Komorebi Hammer - Starting benchmark...")
        print(f"   Projects: {num_projects}, Chunks: {num_chunks}, Concurrency: {concurrent_requests}")
        print()
        
        # Reset counters
        self.latencies = []
        self.successes = 0
        self.failures = 0
        
        start_time = time.perf_counter()
        
        # Check health
        print("🏥 Checking server health...")
        if not await self.check_health():
            print("❌ Server is not healthy!")
            return HammerResult(
                total_requests=1,
                successful_requests=0,
                failed_requests=1,
                total_time_seconds=0,
                requests_per_second=0,
                avg_latency_ms=0,
                min_latency_ms=0,
                max_latency_ms=0,
            )
        print("✅ Server is healthy")
        print()
        
        # Create projects
        print(f"📁 Creating {num_projects} projects...")
        project_ids = []
        for i in range(num_projects):
            project_id = await self.create_project(
                name=f"Hammer Project {i + 1}",
                description=f"Load test project #{i + 1}",
            )
            if project_id:
                project_ids.append(project_id)
        print(f"   Created {len(project_ids)} projects")
        print()
        
        # Create chunks concurrently
        print(f"📝 Capturing {num_chunks} chunks...")
        
        async def capture_random_chunk():
            content = generate_random_content()
            tags = generate_random_tags()
            project_id = random.choice(project_ids) if project_ids else None
            return await self.capture_chunk(content, project_id, tags)
        
        # Run in batches for controlled concurrency
        for batch_start in range(0, num_chunks, concurrent_requests):
            batch_size = min(concurrent_requests, num_chunks - batch_start)
            tasks = [capture_random_chunk() for _ in range(batch_size)]
            await asyncio.gather(*tasks)
            
            # Progress indicator
            progress = min(batch_start + batch_size, num_chunks)
            print(f"   Progress: {progress}/{num_chunks} chunks")
        
        print()
        
        # List and stats operations
        print("📊 Running read operations...")
        for _ in range(10):
            await self.list_chunks(limit=20)
            await self.get_stats()
        print("   Completed read operations")
        print()
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Calculate results
        total_requests = self.successes + self.failures
        rps = total_requests / total_time if total_time > 0 else 0
        
        avg_latency = sum(self.latencies) / len(self.latencies) if self.latencies else 0
        min_latency = min(self.latencies) if self.latencies else 0
        max_latency = max(self.latencies) if self.latencies else 0
        
        result = HammerResult(
            total_requests=total_requests,
            successful_requests=self.successes,
            failed_requests=self.failures,
            total_time_seconds=total_time,
            requests_per_second=rps,
            avg_latency_ms=avg_latency,
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
        )
        
        return result

    async def run_explosion(
        self,
        num_chunks: int = 50,
        concurrent_requests: int = 10,
    ) -> HammerResult:
        """Generate a burst of chunks for a single project to force recursion."""
        print("💥 Komorebi Hammer - Explosion mode...")
        print(f"   Chunks: {num_chunks}, Concurrency: {concurrent_requests}")
        print()
        
        self.latencies = []
        self.successes = 0
        self.failures = 0
        
        start_time = time.perf_counter()
        
        print("🏥 Checking server health...")
        if not await self.check_health():
            print("❌ Server is not healthy!")
            return HammerResult(
                total_requests=1,
                successful_requests=0,
                failed_requests=1,
                total_time_seconds=0,
                requests_per_second=0,
                avg_latency_ms=0,
                min_latency_ms=0,
                max_latency_ms=0,
            )
        print("✅ Server is healthy")
        print()
        
        project_id = await self.create_project(
            name="Hammer Explosion Project",
            description="Force recursive compaction with 50 chunks",
        )
        if not project_id:
            print("❌ Failed to create explosion project")
            return HammerResult(
                total_requests=1,
                successful_requests=0,
                failed_requests=1,
                total_time_seconds=0,
                requests_per_second=0,
                avg_latency_ms=0,
                min_latency_ms=0,
                max_latency_ms=0,
            )
        
        print("📝 Capturing explosion chunks...")
        
        async def capture_explosion_chunk(index: int) -> bool:
            content = generate_explosion_content(index)
            return await self.capture_chunk(content, project_id, tags=["explosion"])
        
        for batch_start in range(0, num_chunks, concurrent_requests):
            batch_size = min(concurrent_requests, num_chunks - batch_start)
            tasks = [
                capture_explosion_chunk(i)
                for i in range(batch_start, batch_start + batch_size)
            ]
            await asyncio.gather(*tasks)
            progress = min(batch_start + batch_size, num_chunks)
            print(f"   Progress: {progress}/{num_chunks} chunks")
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        total_requests = self.successes + self.failures
        rps = total_requests / total_time if total_time > 0 else 0
        
        avg_latency = sum(self.latencies) / len(self.latencies) if self.latencies else 0
        min_latency = min(self.latencies) if self.latencies else 0
        max_latency = max(self.latencies) if self.latencies else 0
        
        return HammerResult(
            total_requests=total_requests,
            successful_requests=self.successes,
            failed_requests=self.failures,
            total_time_seconds=total_time,
            requests_per_second=rps,
            avg_latency_ms=avg_latency,
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
        )


async def main():
    parser = argparse.ArgumentParser(description="Komorebi Hammer - Load testing tool")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the Komorebi server",
    )
    parser.add_argument(
        "--chunks",
        type=int,
        default=50,
        help="Number of chunks to create",
    )
    parser.add_argument(
        "--projects",
        type=int,
        default=3,
        help="Number of projects to create",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Number of concurrent requests",
    )
    parser.add_argument(
        "--mode",
        choices=["standard", "explosion"],
        default="standard",
        help="Run mode: standard benchmark or explosion test",
    )
    
    args = parser.parse_args()
    
    hammer = KomorebiHammer(args.base_url)
    if args.mode == "explosion":
        result = await hammer.run_explosion(
            num_chunks=args.chunks,
            concurrent_requests=args.concurrency,
        )
    else:
        result = await hammer.run_benchmark(
            num_projects=args.projects,
            num_chunks=args.chunks,
            concurrent_requests=args.concurrency,
        )
    
    print(result)
    
    # Exit with error if there were failures
    if result.failed_requests > 0:
        print(f"⚠️  {result.failed_requests} requests failed")
        exit(1)
    else:
        print("✅ All requests successful!")
        exit(0)


if __name__ == "__main__":
    asyncio.run(main())
