const GITHUB_REPO_RE =
  /^https:\/\/(?:www\.)?github\.com\/([A-Za-z0-9_.-]+)\/([A-Za-z0-9_.-]+?)(?:\.git)?\/?$/;

/**
 * Parse a GitHub repo URL into its parts.
 * Accepts https://github.com/owner/name with an optional trailing slash or .git.
 * @param {string} input
 * @returns {{ owner: string, name: string, url: string } | null}
 */
export function parseGithubUrl(input) {
  if (typeof input !== "string") return null;
  const match = input.trim().match(GITHUB_REPO_RE);
  if (!match) return null;
  const [, owner, name] = match;
  if ([owner, name].some((part) => part === "." || part === "..")) return null;
  return { owner, name, url: `https://github.com/${owner}/${name}` };
}

/**
 * Validate user input from the repo form.
 * @param {string} input
 * @returns {{ valid: true, url: string, owner: string, name: string } | { valid: false, error: string }}
 */
export function validateRepoUrl(input) {
  const value = typeof input === "string" ? input.trim() : "";
  if (!value) {
    return { valid: false, error: "Paste a GitHub repository URL to get started." };
  }
  const parsed = parseGithubUrl(value);
  if (!parsed) {
    return {
      valid: false,
      error: "That doesn't look right. Use the form https://github.com/owner/name",
    };
  }
  return { valid: true, ...parsed };
}
