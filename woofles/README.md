# Woofles — Waffles for Dogs

A single-page static site for the Woofles waffle stand. No build step and no
JavaScript framework — just HTML, CSS, four images and an inline SVG icon set.

The only external request is Google Fonts (Plus Jakarta Sans for headings,
Quicksand for body). If a visitor can't reach Google Fonts the page falls back
to Trebuchet MS and still looks fine. To remove the dependency entirely,
download both families into this folder and swap the `<link>` for `@font-face`
rules.

## Design system

Tokens live in the `:root` block at the top of `index.html`:

- **Surfaces** — a warm cream ladder from `--surface` (#FFF9EF) to
  `--surface-variant` (#E8E2D6)
- **Brand** — `--honey` #FFD27D, `--orange` #F2921D (signage), `--blue` #1E8FD5
  (wordmark), `--teal` #006972, `--caramel` #8C5000 for text on honey
- **Ink** — `--bark` #243746 for headings, `--ink-soft` #544435 for body
- **Shape** — radii from 16px to 48px; warm brown-tinted shadows

Motion is opt-out: everything respects `prefers-reduced-motion`, and the
scroll-reveal only hides content once JavaScript has confirmed it can reveal
it again.

## Files

| File | Purpose |
| --- | --- |
| `index.html` | The whole site (all CSS inline) |
| `dog-waffle.jpg` | Hero photo |
| `the-stand.jpg` | "About" photo of the cart |
| `mascot.png` | Cut-out logo mascot (header + footer) |
| `favicon.png` | Browser tab icon |
| `woofles-stand.jpg` | Original source artwork (not used by the page — safe to delete) |
| `deploy.sh` | One-command deploy to an S3 website bucket |

## Hosting on S3

1. Create a bucket, then **Properties → Static website hosting → Enable**,
   index document `index.html`.
2. Upload the contents of this folder to the bucket root (so the site is
   `index.html`, not `woofles/index.html`).
3. Make the objects publicly readable — either via a bucket policy allowing
   `s3:GetObject` on `arn:aws:s3:::YOUR-BUCKET/*` (with Block Public Access
   turned off), or by putting CloudFront in front of the bucket with an
   Origin Access Control, which is the tidier option if you want HTTPS and a
   custom domain.

Or just run the included script, which does all three steps for you:

```sh
./deploy.sh my-woofles-bucket eu-west-2
```

It creates the bucket if needed, sets the public-read policy, turns on website
hosting, and uploads with sensible cache headers. Re-run it any time you change
the page.

## Things to change before going live

- Email address, phone number and social handles in the **Get in touch**
  section and the footer — currently placeholders.
- The event dates under **Where to find us**.
- Prices in the menu cards (taken from the artwork's menu board).
- The contact form uses a `mailto:` action, which opens the visitor's email
  app. S3 can't run server code, so for a proper form use a hosted form
  service (Formspree, Netlify Forms, Basin) and swap the `action` attribute.
