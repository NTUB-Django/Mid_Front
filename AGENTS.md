# Mid_Front requirements

- This is the standalone browser demo cloned from Mid. Preserve original source in reference/mid and original static assets.
- The active Django configuration only serves files. Never enable database-backed accounts, sessions, models, migrations or API mutations here.
- Browser state belongs in localStorage; fixed demo login is ntub / 12345678. Explain that this is demonstration access, not real authentication.
- Preserve the original login and workspace visual design. Keep all active assets local and avoid a required Node build for classroom startup.
- bat contains exactly two BAT files (setup and start) plus a fallback commands TXT. Test startup from a fresh clone and paths with spaces.
- Do not author a new README yet.
- Commit as nasircy <238443453+nasircy@users.noreply.github.com> and push only to NTUB-Django/Mid_Front. Do not deploy this demo over /home/ovis/Mid or change its Cloudflare Tunnel.
- Test browser persistence, import preview/confirm/undo, course and calendar CRUD, social/group demonstrations, role views, route refreshes, and storage failure recovery. No private production data or credentials may be committed.
