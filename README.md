# Amith Raul | AI and Platform Engineering Portfolio

This repository contains practical, small-scale examples of enterprise AI and platform patterns. Each project is built so a reviewer can run it, inspect the design, and understand the tradeoffs.

## Projects

### Governed Agentic BI Demo

An interactive local demo that maps a small set of analytics questions to approved metrics, applies role-based data scopes on the server, and records decisions in an audit log. It uses invented data and a deterministic router so the governance path is visible before any model is added.

- [Project README and run instructions](projects/governed-agentic-bi-demo/README.md)
- [Application code](projects/governed-agentic-bi-demo/app.py)

## How to use this portfolio

Start with the project README, run the example locally, then inspect the code path from request to policy check to query and audit record. The projects are learning artifacts and reference patterns, not production security products.
