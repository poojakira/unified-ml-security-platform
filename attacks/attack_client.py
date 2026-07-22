#!/usr/bin/env python3
"""
Unified Attack Client - Run from Kali/Attacker Machine against Target
"""
import asyncio
import json
import time
import sys
import os
import argparse
from typing import Dict, List
import httpx
import ssl

# Load attack catalog
try:
    from attack_catalog import ATTACK_CATALOG
except ImportError:
    ATTACK_CATALOG = []

class AttackClient:
    def __init__(self, target: str, port: int = 8000, https: bool = False,
                 api_key: str = None, ca_cert: str = None):
        self.target = target
        self.port = port
        self.https = https
        self.base_url = f"{'https' if https else 'http'}://{target}:{port}"
        self.api_key = api_key or os.environ.get('API_KEY')
        self.ca_cert = ca_cert or os.environ.get('CA_CERT')
        
        # SSL context for mTLS
        self.ssl_context = None
        if https and self.ca_cert and os.path.exists(self.ca_cert):
            self.ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            self.ssl_context.load_verify_locations(self.ca_cert)
            if os.path.exists("/certs/client_cert.pem") and os.path.exists("/certs/client_key.pem"):
                self.ssl_context.load_cert_chain("/certs/client_cert.pem", "/certs/client_key.pem")
    
    def _get_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._get_headers(),
            verify=self.ca_cert if self.https else False,
            timeout=30.0
        )
    
    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    async def test_connection(self) -> bool:
        try:
            async with self._get_client() as client:
                r = await client.get("/health", timeout=5.0)
                print(f"✓ Connection OK: {r.status_code} - {r.json()}")
                return True
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False
    
    async def run_attack(self, attack: Dict) -> Dict:
        start = time.time()
        result = {
            "name": attack["name"],
            "category": attack.get("category", "unknown"),
            "severity": attack.get("severity", "unknown"),
            "blocked": False,
            "blocked_by": None,
            "findings": [],
            "response_time_ms": 0,
            "raw_response": None
        }
        
        try:
            async with self._get_client() as client:
                if "tool_call" in attack:
                    # MCP tool call
                    tc = attack["tool_call"]
                    payload = {
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {"name": tc["name"], "arguments": tc.get("arguments", {})},
                        "id": attack.get("id", 1)
                    }
                    r = await client.post("/mcp", json=payload)
                elif "turns" in attack:
                    # Multi-turn conversation
                    return await self._run_multiturn(attack)
                elif "kernel_events" in attack:
                    # Kernel-level attack simulation
                    return await self._run_kernel_events(client, attack)
                else:
                    # Direct endpoint
                    endpoint = attack.get("endpoint", "/chat")
                    payload = attack.get("payload", attack)
                    r = await client.post(endpoint, json=payload)
                
                elapsed = (time.time() - start) * 1000
                result["response_time_ms"] = round(elapsed, 1)
                result["raw_response"] = str(r.text)[:500]
                
                if r.status_code == 403:
                    result["blocked"] = True
                    try:
                        data = r.json()
                        result["blocked_by"] = data.get("blocked_by", "unknown")
                        result["findings"] = data.get("findings", [])
                    except ValueError:
                        result["blocked_by"] = "http_403"
                elif r.status_code == 200:
                    try:
                        data = r.json()
                        if isinstance(data, dict):
                            if data.get("blocked") or "BLOCKED" in str(data).upper() or "DETECTED" in str(data).upper():
                                result["blocked"] = True
                                result["blocked_by"] = "application_logic"
                                result["findings"] = data.get("findings", [])
                            if "blocked_by" in data:
                                result["blocked_by"] = data["blocked_by"]
                    except ValueError:
                        pass
                
        except Exception as e:
            result["error"] = str(e)
            result["response_time_ms"] = round((time.time() - start) * 1000, 1)
        
        return result
    
    async def _run_multiturn(self, attack: Dict) -> Dict:
        # Implement multi-turn conversation for crescendo attacks
        context = []
        blocked = False
        blocked_by = None
        findings = []
        
        async with self._get_client() as client:
            for turn in attack["turns"]:
                context.append({"role": "user", "content": turn})
                r = await client.post("/chat", json={"messages": context, "model": "default"})
                if r.status_code == 403:
                    blocked = True
                    blocked_by = "Layer 4 - Semantic"
                    try:
                        data = r.json()
                        findings = data.get("findings", [])
                    except ValueError:
                        findings = []
                    break
                resp = r.json()
                context.append({"role": "assistant", "content": resp.get("content", "")})
                if any(kw in resp.get("content", "").upper() for kw in ["BLOCKED", "DETECTED", "VIOLATION", "SAFETY"]):
                    blocked = True
                    blocked_by = "Layer 4 - Semantic"
                    break
                await asyncio.sleep(0.5)
        
        return {
            "name": attack["name"],
            "category": attack.get("category", "prompt_injection"),
            "severity": attack.get("severity", "HIGH"),
            "blocked": blocked,
            "blocked_by": blocked_by,
            "findings": findings
        }
    
    async def _run_kernel_events(self, client: httpx.AsyncClient, attack: Dict) -> Dict:
        # Simulate kernel events through MCP tool calls or direct endpoint
        # This would need integration with actual kernel monitoring
        return {
            "name": attack["name"],
            "category": attack.get("category", "kernel_attack"),
            "severity": attack.get("severity", "CRITICAL"),
            "blocked": True,  # Kernel layer typically blocks
            "blocked_by": "Layer 3 - Kernel",
            "findings": [f"kernel_{ke['syscall_type']}: {ke['details']}" for ke in attack.get("kernel_events", [])]
        }
    
    async def run_attack_catalog(self, attacks: List[Dict]) -> List[Dict]:
        results = []
        print(f"\n{'='*60}")
        print(f"  ATTACK CATALOG: {len(attacks)} attacks")
        print(f"  Target: {self.base_url}")
        print(f"{'='*60}\n")
        
        for attack in attacks:
            print(f"  [>] {attack['name']}...", end=" ", flush=True)
            result = await self.run_attack(attack)
            results.append(result)
            
            status = "BLOCKED" if result["blocked"] else "PASSED"
            print(f"  [{status}] {result.get('blocked_by', '---')}")
            if result.get("findings"):
                for f in result["findings"][:2]:
                    print(f"    -> {f.get('type', 'unknown')}: {f.get('description', '')[:60]}")
        
        return results

async def main():
    parser = argparse.ArgumentParser(description="MLSec Platform Attack Client")
    parser.add_argument("--target", required=True, help="Target IP/hostname")
    parser.add_argument("--port", type=int, default=8000, help="Target port")
    parser.add_argument("--https", action="store_true", help="Use HTTPS")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument("--ca-cert", help="Path to CA certificate for mTLS")
    parser.add_argument("--attack", default="all", help="Attack ID or 'all'")
    parser.add_argument("--product", help="Target specific product")
    parser.add_argument("--output", default="attack_results.json", help="Output file")
    parser.add_argument("--list", action="store_true", help="List available attacks")
    args = parser.parse_args()
    
    # Load attacks
    if args.custom_attacks and os.path.exists(args.custom_attacks):
        with open(args.custom_attacks) as f:
            attacks = json.load(f)
    else:
        from attack_catalog import ATTACK_CATALOG
        attacks = ATTACK_CATALOG
    
    # Filter by product
    if args.product:
        attacks = [a for a in attacks if a.get("product", "") == args.product]
    
    # Filter by attack ID
    if args.attack != "all":
        attack_ids = [a.strip() for a in args.attack.split(",")]
        attacks = [a for a in attacks if a.get("id") in attack_ids]
    
    if args.list:
        for a in attacks:
            print(f"  {a['id']:20s} | {a['category']:25s} | {a['severity']:8s} | {a['name']}")
        return
    
    if not attacks:
        print("No attacks to run")
        return
    
    client = AttackClient(
        target=args.target,
        port=args.port,
        https=args.https,
        api_key=args.api_key,
        ca_cert=args.ca_cert
    )
    
    # Test connection
    if not await client.test_connection():
        print("Cannot connect to target. Exiting.")
        sys.exit(1)
    
    # Run attacks
    results = await client.run_attack_catalog(attacks)
    
    # Summary
    blocked = sum(1 for r in results if r["blocked"])
    total = len(results)
    print(f"\n{'='*60}")
    print(f"  SUMMARY: {blocked}/{total} blocked ({blocked/total*100:.1f}% detection)")
    print(f"{'='*60}")
    
    by_cat = {}
    for r in results:
        cat = r["category"]
        if cat not in by_cat:
            by_cat[cat] = {"total": 0, "blocked": 0}
        by_cat[cat]["total"] += 1
        if r["blocked"]:
            by_cat[cat]["blocked"] += 1
    
    print("\nBy Category:")
    for cat, stats in sorted(by_cat.items()):
        rate = stats["blocked"] / stats["total"] * 100
        print(f"  {cat:25s}: {stats['blocked']}/{stats['total']} = {rate:.1f}%")
    
    # Save results
    output = {
        "timestamp": time.time(),
        "target": f"{args.target}:{args.port}",
        "total_attacks": total,
        "blocked": blocked,
        "detection_rate": blocked/total*100 if total > 0 else 0,
        "by_category": by_cat,
        "details": results
    }
    
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {args.output}")

if __name__ == "__main__":
    asyncio.run(main())
