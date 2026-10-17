# Amith Raul | AI and Platform Engineering Portfolio

This repository contains practical examples of enterprise AI and platform patterns. Each project is designed so you can run it locally, inspect the code, and understand the design decisions.

## Projects

### Governed Agentic BI Demo

A local analytics demo that routes a small set of questions to approved metrics, applies role scopes on the server, and records decisions in an audit log. It uses synthetic data and a deterministic router so the governance path is easy to understand before adding an AI model.

- [Project guide](projects/governed-agentic-bi-demo/README.md)
- [Application code](projects/governed-agentic-bi-demo/app.py)

## How to explore

Start with the project guide, run the app locally, and trace a request from the browser through intent classification, role policy, query, and audit record. These are learning prototypes, not production security products.
