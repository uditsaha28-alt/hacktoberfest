// Display metadata for the agent's tools (names are fixed by the API contract).
export const TOOL_META = {
  get_repo_tree: { label: "Scanning repo tree", icon: "tree" },
  read_file: { label: "Reading file", icon: "file" },
  search_code: { label: "Searching code", icon: "search" },
  list_issues: { label: "Checking open issues", icon: "issue" },
  write_section: { label: "Writing section", icon: "pen" },
};

export function toolLabel(tool) {
  return TOOL_META[tool]?.label ?? tool ?? "Working";
}

export function toolIconName(tool) {
  return TOOL_META[tool]?.icon ?? "file";
}

/** One short line describing what a tool call is targeting. */
export function argsPreview(args) {
  if (!args || typeof args !== "object") return "";
  if (args.path !== undefined) return args.path === "" ? "/" : String(args.path);
  if (args.query) return `"${args.query}"`;
  if (args.key) return String(args.key);
  if (args.labels) return String(args.labels);
  const first = Object.values(args)[0];
  return first === undefined ? "" : String(first);
}
