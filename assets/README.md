# assets/

Every media asset for Handovers: logos, backgrounds, screenshots, diagrams exported as images,
and video thumbnails.

| Folder | Contents |
|---|---|
| `logos/` | Brand marks. `master-logo.png` (1536×1024, icon + wordmark) is the source logo. `logo-mark.png` (icon only, tightly cropped) and `logo-full.png` (icon + wordmark, tightly cropped) are derived from it and used by the frontend; `logo-mark-alpha.png` is `logo-mark.png` with a transparent background (white made transparent, edges kept), used by the app's sidebar and sign-in page so the mark sits on both the light and dark themes; `logo-nav.png` and `favicon.png` provide the 144×96 brand icon and web favicon across the app and site |
| `backgrounds/` | Background images for slides, the demo video and the website |
| `screenshots/` | Product screenshots for the README and the submission, numbered in demo order (`01-overview-risk.jpg` …). Taken from the seeded sample company; no real people or data |

## Rules

- Put media here, not in feature folders. Apps reference or copy from `assets/`.
- Use lowercase kebab-case file names that describe the asset (e.g. `logo-icon-dark.png`).
- Never overwrite `logos/master-logo.png`. Add variants (sizes, dark mode, icon-only) as new files.
- Keep files reasonably small. Export web-ready PNG/SVG/WebP and avoid uncompressed originals over ~5 MB.
- Only commit assets we have the right to use. Note the source of any third-party asset here.
