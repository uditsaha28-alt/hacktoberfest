import { parseGithubUrl, validateRepoUrl } from "../lib/validators.js";

describe("parseGithubUrl", () => {
  it("parses a plain repo url", () => {
    expect(parseGithubUrl("https://github.com/facebook/react")).toEqual({
      owner: "facebook",
      name: "react",
      url: "https://github.com/facebook/react",
    });
  });

  it("tolerates a trailing slash, .git suffix and surrounding whitespace", () => {
    expect(parseGithubUrl("  https://github.com/a/b/  ").url).toBe("https://github.com/a/b");
    expect(parseGithubUrl("https://github.com/a/b.git").url).toBe("https://github.com/a/b");
  });

  it("keeps dots, dashes and underscores in names", () => {
    expect(parseGithubUrl("https://github.com/my-org/some_repo.js").name).toBe("some_repo.js");
  });

  it("rejects non-github hosts, missing parts and extra path segments", () => {
    expect(parseGithubUrl("https://gitlab.com/a/b")).toBeNull();
    expect(parseGithubUrl("https://github.com/onlyowner")).toBeNull();
    expect(parseGithubUrl("https://github.com/a/b/issues")).toBeNull();
    expect(parseGithubUrl("http://github.com/a/b")).toBeNull();
    expect(parseGithubUrl("github.com/a/b")).toBeNull();
  });

  it("rejects dot segments and non-strings", () => {
    expect(parseGithubUrl("https://github.com/../b")).toBeNull();
    expect(parseGithubUrl(null)).toBeNull();
    expect(parseGithubUrl(42)).toBeNull();
  });
});

describe("validateRepoUrl", () => {
  it("returns the normalized url when valid", () => {
    const result = validateRepoUrl("https://github.com/a/b/");
    expect(result.valid).toBe(true);
    expect(result.url).toBe("https://github.com/a/b");
  });

  it("asks for input when empty", () => {
    const result = validateRepoUrl("   ");
    expect(result.valid).toBe(false);
    expect(result.error).toContain("Paste");
  });

  it("explains the expected format when invalid", () => {
    const result = validateRepoUrl("not a url");
    expect(result.valid).toBe(false);
    expect(result.error).toContain("https://github.com/owner/name");
  });
});
