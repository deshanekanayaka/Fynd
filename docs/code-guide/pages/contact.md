---
id: "contact"
title: "contact.py"
group: "Shared foundations"
order: 4
source: "src/fynd/contact.py"
summary: "Builds the operator contact details used by OpenAlex and file-fetching requests."
related: ["openalex", "fetcher", "cli"]
updated: "2026-11-08"
---

## Why this file exists

A host receiving automated downloads should be able to identify Fynd and contact its operator. Reading the address from the environment keeps a personal address out of source code.

The **operator** is the person running Fynd. OpenAlex uses this file for its `mailto` query parameter and User-Agent header. The file downloader uses the same User-Agent when requesting robots.txt and PDF files. Claude, Voyage, and Semantic Scholar do not use these helpers in the current code.

## The flow

1. **Environment**

   FYND_CONTACT_EMAIL supplies the operator address.

2. **Contact string**

   Read and check that it is present.

3. **Request header**

   Build a User-Agent naming Fynd and its repository.

## A small example

```text Illustrative User-Agent
Fynd/0.1 (+https://github.com/deshanekanayaka/Fynd; operator@example.org)
```

A **User-Agent** is an HTTP header identifying the program making a request. Here it names Fynd, links to the repository, and provides the operator's email address.

### Where does the address come from?

```text Illustrative local .env setting
FYND_CONTACT_EMAIL=operator@example.org
```

The CLI loads `.env` into the process environment. `contact.py` reads the environment variable; it does not open `.env` itself. `contact_email` removes leading and trailing whitespace, then raises `ContactEmailMissing` if the result is empty. It checks presence, not whether the address is correctly formatted or can receive mail.

There is no default address: the person running Fynd must supply one. The existing `.gitignore` keeps `.env` out of the repository.

## The pieces inside

| Name                  | What it does                                                          |
| --------------------- | --------------------------------------------------------------------- |
| `ContactEmailMissing` | Raised when FYND_CONTACT_EMAIL is missing or blank.                   |
| `contact_email`       | Returns the configured address; it checks presence, not email syntax. |
| `user_agent`          | Builds the identification string used by OpenAlex and the fetcher.    |
