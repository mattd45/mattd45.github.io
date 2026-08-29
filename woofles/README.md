# Woofles — Waffles for Dogs

A single-page static site for the Woofles waffle stand. No build step, no
dependencies — just HTML, CSS and four images.

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
