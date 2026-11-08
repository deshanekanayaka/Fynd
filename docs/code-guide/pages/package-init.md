---
id: "package-init"
title: "__init__.py"
group: "Running and checking"
order: 623
source: "src/fynd/__init__.py"
summary: "Marks fynd as a Python package and describes the backend modules it contains."
related: ["cache", "stages-init"]
updated: "2026-11-08"
---

## Why this file exists

The package marker gives imports such as `from fynd import cache` a regular package boundary. Its docstring describes the Topic selection, Paper reading, and measurement modules. Importing the marker itself starts no command or external request.

## The flow

1. **Import**

   Python loads the package.

2. **Description**

   The docstring identifies Fynd.

3. **Submodule**

   The requested module supplies the actual behaviour.

## A small example

```text An import
from fynd import cache
# Loads the package and then its cache module.
```

## The pieces inside

| Name                | What it does                                                 |
| ------------------- | ------------------------------------------------------------ |
| `Package docstring` | Describes the backend modules and how the CLI connects them. |
