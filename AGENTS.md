# MID project requirements

- Preserve the established login page design. Registration uses that same design, with separate student-number and email fields. Do not redesign unrelated pages.
- Author and commit as nasircy using the repository's configured identity.
- Every push to GitHub must be followed in the same task by deployment to the Ovis Linux Server production checkout at /home/ovis/Mid and verification of https://class2dj.nsir.uk. A successful push alone is not completion.
- Back up the production SQLite database before migrations or deployment. Preserve existing accounts, selections, and schedules. Do not commit databases, passwords, tunnel tokens, or runtime configuration.
- The private repository can be deployed through a Git bundle transferred over the existing SSH connection. Verify the pushed SHA, require a clean production checkout, and prefer fast-forward updates.
- Apply required migrations, collect static files, restart mid-web.service, and verify both mid-web and cloudflared remain active. The server's existing Cloudflare Tunnel is "Ovis Vmware Server"; preserve its other routes and do not reinstall it. Do not change Docker or containerd on this shared server unless the user requests it.
- Use a single lightweight browser tab for UI checks and stop temporary QA servers and SSH tunnels afterward.
- Do not restore the removed Classroom startup workflow or its operating-system matrix.
