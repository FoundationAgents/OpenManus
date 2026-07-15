---
name: docker
type: knowledge
version: 1.0
agent: Manus
triggers:
  - docker
  - container
  - compose
  - port
  - server
---
Docker workflow:
1. Inspect `docker compose ps`, container logs, and exposed ports before guessing.
2. Keep long-running dev servers in the background and write logs to a file in the conversation workspace.
3. After starting a server, verify it is listening with `ss -tlnp` or `curl`.
4. Report the reachable URL and leave enough runtime evidence for the UI process panel.
5. Do not stop OpenManus system containers unless explicitly asked.
