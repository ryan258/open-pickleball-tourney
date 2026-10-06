# Community poster theme

Ryan supplied a vintage pickleball homepage reference and requested that the
home page and site theme follow it. He also specified WebP for the images.
The implementation keeps every heading, control and example score live HTML;
artwork is decorative and has empty alternative text. Essential information
does not depend on an illustration.

Palette: warm cream `#f5f0df`, forest green `#103b32`, vermilion `#c94429`,
gold `#edc259`, dusty blue `#78a2ae`. Small error text uses darker red
`#ad3525`. Paper grain is a small inline SVG filter in CSS. The court mark is
SVG. Anton is bundled locally from the Google Fonts repository, with its SIL
Open Font License at `static/licenses/Anton-OFL.txt`. Body and form text uses
the system sans-serif stack.

## Artwork and processing

Both images were created with the built-in image-generation tool, using Ryan's
attached image as a visual reference and requesting true transparency. No API
or CLI image-generation fallback was used. The tool's original PNG outputs
remain outside the repository; only their WebP conversions are site assets.
Transparency was retained with lossless alpha.

| Asset | Dimensions | Bytes | Conversion |
| --- | --- | --- | --- |
| `assets/images/pickleball-poster.webp` | 1448 × 1086 | 293,402 | `cwebp -q 86 -m 6` |
| `assets/images/pickleball-community.webp` | 800 × 400 | 59,964 | `cwebp -resize 800 0 -q 86 -m 6` |

Hugo fingerprints and serves the WebP assets directly, without a PNG/JPEG
fallback. The service worker includes both images and the font in its shell
cache. The portable edition includes these same files and uses relative paths.

## Final hero prompt

Use case: background-extraction / compositing. Asset type: a transparent hero
illustration for the website shown in the reference. Extract and recreate just
its vintage cut-paper pickleball sports illustration as a polished standalone
asset, with NO typography, NO words, NO website UI, NO scorecard, NO border.
Keep the expressive lunging player silhouette in very dark forest green,
cream cut-paper outline, dynamic outstretched paddle toward an airborne golden
perforated pickleball on the upper right. Keep the tilted vermilion-red
rectangular block behind the player, the large mustard-gold sun disk, a muted
dusty blue geometric area at right, and a dark court-green ground wedge with
cream court lines across the bottom. Use subtle authentic silkscreen ink grain
and slightly irregular hand-cut edges. Composition: landscape approximately
4:3; complete figure from cap to both shoes visible; player mainly left/center,
paddle and ball high/right, lower right relatively clear so a live HTML
scorecard can sit there. Generous transparent negative space outside the art
silhouette, no cream rectangular background. Preserve the reference's palette,
angular 1930s sports poster energy and approachable neighborhood feel. This is
a website artwork asset, not a mockup of the website.

## Final community prompt

Create the small lower-right community illustration from this reference as an
isolated decorative asset for a website. Four neighborhood pickleball players
standing at a net, two players high-fiving in the middle. Angular vintage
cut-paper silhouettes, screenprint grain, very dark forest green with
vermilion-red accents, one mustard-gold sun disk behind them. Torsos and heads
visible above a simple net that angles gently along bottom. Warm cream thin net
lines. All four figures must fit inside the image. Wide horizontal 2:1
composition. Actual transparent background outside the players, net, and sun.
NO text, NO letters, NO logo, NO interface, NO border, NO page background. Match
the style and palette of the reference's small bottom-right vignette. This is
a small decorative website illustration, not a website screenshot.
