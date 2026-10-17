# Amith Raul | AI and Platform Engineering Portfolio

This repository contains practical, small-scale examples of enterprise AI and platform patterns. Each project is built so a reviewer can run it, inspect the design, and understand the tradeoffs.

## Projects

### Governed Agentic BI Demo

An interactive local demo that maps a small set of analytics questions to approved metrics, applies role-based data scopes on the server, and records decisions in an audit log. It uses invented data and a deterministic router so the governance path is visible before any model is added.

- [Project README and run instructions](projects/governed-agentic-bi-demo/README.md)
- [Application code](projects/governed-agentic-bi-demo/app.py)

### FinOps Cloud Cost Workbench

A local dashboard over synthetic cloud spend. It compares team budgets, shows spend without owner tags, and flags material service-cost increases using a transparent deterministic rule. Automated tests cover the calculations and filters.

- [Project README and run instructions](projects/finops-cloud-cost-workbench/README.md)
- [Dashboard application](projects/finops-cloud-cost-workbench/app.py)
- [Test evidence](projects/finops-cloud-cost-workbench/evidence/test-results.txt)

### MCP Analytics Server

A local Model Context Protocol server that makes read-only portfolio analytics discoverable as structured tools over synthetic enterprise AI program data. It includes an MCP resource, a review prompt, and in-memory client tests.

- [Project README and run instructions](projects/mcp-analytics-server/README.md)
- [MCP server](projects/mcp-analytics-server/server.py)
- [Test evidence](projects/mcp-analytics-server/evidence/test-results.txt)
- [Inspector demo and local test screenshots](projects/mcp-analytics-server/evidence/)

### AI Observability & Evaluation Starter

A local dashboard for synthetic AI traces, deterministic quality and safety gates, and release comparisons across latency, pass rate, and illustrative cost.

- [Project README and run instructions](projects/ai-observability-evaluation-starter/README.md)
- [Dashboard application](projects/ai-observability-evaluation-starter/app.py)
- [Evaluation logic](projects/ai-observability-evaluation-starter/observability.py)
- [Automated test output](projects/ai-observability-evaluation-starter/evidence/test-results.txt)
- [Local dashboard and test screenshots](projects/ai-observability-evaluation-starter/evidence/)

### Enterprise Agent Control Plane

A local governance simulation for agent registration, tool and data-scope policies, cost limits, human approval gates, and decision auditing. It records requests and decisions in memory; it never invokes an agent or executes a tool.

- [Project README and run instructions](projects/enterprise-agent-control-plane/README.md)
- [Control-plane policy model](projects/enterprise-agent-control-plane/control_plane.py)
- [Automated test output](projects/enterprise-agent-control-plane/evidence/test-results.txt)
- [Local dashboard and approval audit screenshots](projects/enterprise-agent-control-plane/evidence/)

## How to use this portfolio

Start with the project README, run the example locally, then inspect the code path from request to policy check to query and audit record. The projects are learning artifacts and reference patterns, not production security products.
