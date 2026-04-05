# Documentation Structure

This folder is organized into two distinct sections:

## 📦 `user/` — End-User Documentation

**Ship this with your product.** Contains guides, configuration references, API docs, and security information that users need to successfully use the tool.

- **user-guide.md** — Feature overview and tutorials
- **configuration.md** — All CLI options and settings
- **api-reference.md** — Programmatic API
- **security.md** — Security and privacy practices
- **contributing.md** — Contribution guidelines
- **assets/** — Visual media

[→ See user/README.md for details](user/README.md)

---

## 🔒 `internal/` — Internal & Business Documentation

**Keep this private.** Contains technical architecture, business strategy, marketing plans, deployment guides, and internal audit findings.

- **architecture.md** — System design & technical details
- **Phase 1 planning** — Launch timeline and strategy
- **marketing/** — Marketing strategy, templates, and outreach assets
- **deployment/** — Internal deployment procedures
- **user-feedback/** — Feedback collection and analytics
- **audit-report.md** — Technical debt & audit findings

[→ See internal/README.md for details](internal/README.md)

---

## Quick Checklist

**Before shipping to users:**
- ✅ Include everything from `user/` 
- ✅ Exclude everything from `internal/`
- ✅ Update relative links if needed
- ✅ Verify asset paths work in distribution context

**Before pushing to public repository:**
- ✅ Make sure `internal/` folder is in `.gitignore` (or at least not committed if sensitive)
- ✅ Only include `user/` docs in documentation builds
