const base = {
  viewBox: "0 0 20 20",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
};

const make = (paths) =>
  function Icon({ className = "h-4 w-4" }) {
    return (
      <svg {...base} className={className}>
        {paths}
      </svg>
    );
  };

export const CheckIcon = make(<path d="M4 10.5l4 4 8-9" />);
export const XIcon = make(<path d="M5 5l10 10M15 5L5 15" />);
export const TreeIcon = make(<path d="M4 4h5l1.5 2H16v9H4zM4 8h12" />);
export const FileIcon = make(<path d="M6 3h5l4 4v10H6zM11 3v4h4" />);
export const SearchIcon = make(
  <>
    <circle cx="9" cy="9" r="5" />
    <path d="M13 13l4 4" />
  </>
);
export const IssueIcon = make(
  <>
    <circle cx="10" cy="10" r="7" />
    <path d="M10 6.5v4M10 13.5h.01" />
  </>
);
export const PenIcon = make(<path d="M4 16l1-4 8-8 3 3-8 8zM12 5l3 3" />);
export const ArrowRightIcon = make(<path d="M4 10h12M11 5l5 5-5 5" />);
export const ExternalIcon = make(<path d="M8 5H5v10h10v-3M11 4h5v5M16 4l-7 7" />);
export const CopyIcon = make(
  <>
    <rect x="7" y="7" width="9" height="9" rx="1.5" />
    <path d="M13 7V5a1.5 1.5 0 0 0-1.5-1.5H5A1.5 1.5 0 0 0 3.5 5v6.5A1.5 1.5 0 0 0 5 13h2" />
  </>
);
export const DownloadIcon = make(<path d="M10 3v9M6 8.5l4 4 4-4M4 16h12" />);
export const RefreshIcon = make(<path d="M16 10a6 6 0 1 1-2-4.5M16 3v3.5h-3.5" />);
export const AlertIcon = make(
  <>
    <path d="M10 3l8 14H2z" />
    <path d="M10 8.5v3.5M10 14.5h.01" />
  </>
);
export const SparkIcon = make(<path d="M10 3l1.8 4.7L16.5 9.5l-4.7 1.8L10 16l-1.8-4.7L3.5 9.5l4.7-1.8z" />);

export function SpinnerIcon({ className = "h-4 w-4" }) {
  return (
    <svg viewBox="0 0 20 20" fill="none" className={`${className} animate-spin`} aria-hidden="true">
      <circle cx="10" cy="10" r="7" stroke="currentColor" strokeOpacity="0.25" strokeWidth="2.2" />
      <path d="M17 10a7 7 0 0 0-7-7" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}

export function GithubIcon({ className = "h-4 w-4" }) {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className={className} aria-hidden="true">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.5 7.5 0 0 1 4 0c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z" />
    </svg>
  );
}
